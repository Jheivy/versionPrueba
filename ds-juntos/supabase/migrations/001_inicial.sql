-- =====================================================================
--  DS Juntos - esquema inicial de Supabase
--  Pegadlo en Supabase > SQL Editor y ejecutadlo una vez.
-- =====================================================================

-- ---------- Tablas ----------
create table public.parejas (
  id      uuid primary key default gen_random_uuid(),
  codigo  text unique not null,
  creada  timestamptz not null default now()
);

create table public.perfiles (
  id         uuid primary key references auth.users (id) on delete cascade,
  pareja_id  uuid references public.parejas (id) on delete set null,
  nombre     text not null check (char_length(nombre) between 1 and 30),
  color      text not null default '#4F7CFF',
  creado     timestamptz not null default now()
);

create table public.juegos (
  id           uuid primary key default gen_random_uuid(),
  pareja_id    uuid not null references public.parejas (id) on delete cascade,
  titulo       text not null,
  sistema      text not null,
  rom_sha1     text not null,
  modo_juntos  text not null default 'turnos'
               check (modo_juntos in ('netplay', 'wiimmfi', 'cableLink', 'redLocal', 'turnos')),
  anadido_por  uuid references public.perfiles (id) on delete set null default auth.uid(),
  creado       timestamptz not null default now(),
  unique (pareja_id, rom_sha1)
);

-- Una partida guardada por juego (compartida por la pareja).
create table public.partidas (
  juego_id         uuid primary key references public.juegos (id) on delete cascade,
  sha1             text,
  version          integer not null default 0,
  subida_por       uuid references public.perfiles (id) on delete set null,
  actualizada      timestamptz not null default now(),
  bloqueada_por    uuid references public.perfiles (id) on delete set null,
  bloqueada_hasta  timestamptz
);

create table public.invitaciones (
  id            uuid primary key default gen_random_uuid(),
  pareja_id     uuid not null references public.parejas (id) on delete cascade,
  de            uuid not null references public.perfiles (id) on delete cascade default auth.uid(),
  juego_id      uuid not null references public.juegos (id) on delete cascade,
  estado        text not null default 'pendiente'
                check (estado in ('pendiente', 'aceptada', 'rechazada', 'cancelada')),
  ip_anfitrion  text,
  creada        timestamptz not null default now()
);

create table public.mensajes (
  id         bigint generated always as identity primary key,
  pareja_id  uuid not null references public.parejas (id) on delete cascade,
  de         uuid not null references public.perfiles (id) on delete cascade default auth.uid(),
  tipo       text not null default 'texto' check (tipo in ('texto', 'toque')),
  texto      text check (char_length(texto) <= 1000),
  creado     timestamptz not null default now()
);
create index mensajes_pareja_creado on public.mensajes (pareja_id, creado desc);

-- ---------- Funciones ----------
-- Pareja del usuario actual (se usa en las politicas).
create function public.mi_pareja() returns uuid
language sql stable security definer set search_path = public as $$
  select pareja_id from public.perfiles where id = auth.uid()
$$;

-- Crea una pareja y mete en ella al usuario. Devuelve el codigo para compartir.
create function public.crear_pareja() returns text
language plpgsql security definer set search_path = public as $$
declare
  letras constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  nuevo text;
  pid uuid;
begin
  if auth.uid() is null then raise exception 'Sin sesion'; end if;
  loop
    nuevo := '';
    for i in 1..6 loop
      nuevo := nuevo || substr(letras, 1 + floor(random() * length(letras))::int, 1);
    end loop;
    exit when not exists (select 1 from public.parejas where codigo = nuevo);
  end loop;
  insert into public.parejas (codigo) values (nuevo) returning id into pid;
  update public.perfiles set pareja_id = pid where id = auth.uid();
  return nuevo;
end $$;

-- Se une a la pareja del codigo (maximo dos personas).
create function public.unirse_pareja(p_codigo text) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  pid uuid;
begin
  if auth.uid() is null then raise exception 'Sin sesion'; end if;
  select id into pid from public.parejas where codigo = upper(trim(p_codigo));
  if pid is null then raise exception 'Codigo no valido'; end if;
  if (select count(*) from public.perfiles where pareja_id = pid and id <> auth.uid()) >= 2 then
    raise exception 'Esta pareja ya esta completa';
  end if;
  update public.perfiles set pareja_id = pid where id = auth.uid();
  return pid;
end $$;

-- Reserva la partida para jugar (candado con caducidad). true si se consigue.
create function public.bloquear_partida(p_juego uuid, p_minutos integer default 240) returns boolean
language plpgsql security definer set search_path = public as $$
declare
  filas integer;
begin
  if not exists (select 1 from public.juegos where id = p_juego and pareja_id = public.mi_pareja()) then
    raise exception 'Juego no encontrado';
  end if;
  insert into public.partidas (juego_id) values (p_juego) on conflict (juego_id) do nothing;
  update public.partidas
     set bloqueada_por = auth.uid(),
         bloqueada_hasta = now() + make_interval(mins => p_minutos)
   where juego_id = p_juego
     and (bloqueada_por is null or bloqueada_hasta < now() or bloqueada_por = auth.uid());
  get diagnostics filas = row_count;
  return filas = 1;
end $$;

create function public.desbloquear_partida(p_juego uuid) returns void
language sql security definer set search_path = public as $$
  update public.partidas set bloqueada_por = null, bloqueada_hasta = null
   where juego_id = p_juego and bloqueada_por = auth.uid()
     and exists (select 1 from public.juegos j where j.id = p_juego and j.pareja_id = public.mi_pareja())
$$;

-- Registra una subida. Falla si alguien subio otra version entretanto.
create function public.registrar_subida(p_juego uuid, p_sha1 text, p_version_previa integer) returns integer
language plpgsql security definer set search_path = public as $$
declare
  nueva integer;
begin
  update public.partidas
     set sha1 = p_sha1, version = version + 1, subida_por = auth.uid(), actualizada = now()
   where juego_id = p_juego and version = p_version_previa
     and exists (select 1 from public.juegos j where j.id = p_juego and j.pareja_id = public.mi_pareja())
  returning version into nueva;
  if nueva is null then raise exception 'La partida cambio mientras tanto'; end if;
  return nueva;
end $$;

-- Crea el perfil al registrarse (el nombre llega en los metadatos).
create function public.crear_perfil() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.perfiles (id, nombre)
  values (new.id, coalesce(nullif(new.raw_user_meta_data ->> 'nombre', ''), split_part(new.email, '@', 1)));
  return new;
end $$;

create trigger al_registrarse after insert on auth.users
  for each row execute function public.crear_perfil();

-- ---------- Seguridad (RLS) ----------
alter table public.parejas     enable row level security;
alter table public.perfiles    enable row level security;
alter table public.juegos      enable row level security;
alter table public.partidas    enable row level security;
alter table public.invitaciones enable row level security;
alter table public.mensajes    enable row level security;

create policy "ver mi pareja" on public.parejas for select using (id = public.mi_pareja());

create policy "ver perfiles de mi pareja" on public.perfiles for select
  using (id = auth.uid() or pareja_id = public.mi_pareja());
create policy "editar mi perfil" on public.perfiles for update
  using (id = auth.uid()) with check (id = auth.uid() and pareja_id is not distinct from public.mi_pareja());

create policy "juegos de mi pareja" on public.juegos for all
  using (pareja_id = public.mi_pareja()) with check (pareja_id = public.mi_pareja());

create policy "ver partidas de mi pareja" on public.partidas for select
  using (exists (select 1 from public.juegos j where j.id = juego_id and j.pareja_id = public.mi_pareja()));

create policy "invitaciones de mi pareja" on public.invitaciones for all
  using (pareja_id = public.mi_pareja()) with check (pareja_id = public.mi_pareja());

create policy "leer mensajes de mi pareja" on public.mensajes for select using (pareja_id = public.mi_pareja());
create policy "escribir mensajes" on public.mensajes for insert
  with check (pareja_id = public.mi_pareja() and de = auth.uid());

-- ---------- Archivos de partidas ----------
-- Ruta: partidas/{pareja_id}/{juego_id}/actual.srm  e  historial/{version}.srm
insert into storage.buckets (id, name, public) values ('partidas', 'partidas', false)
  on conflict (id) do nothing;

create policy "partidas: leer" on storage.objects for select
  using (bucket_id = 'partidas' and (storage.foldername(name))[1] = public.mi_pareja()::text);
create policy "partidas: subir" on storage.objects for insert
  with check (bucket_id = 'partidas' and (storage.foldername(name))[1] = public.mi_pareja()::text);
create policy "partidas: reemplazar" on storage.objects for update
  using (bucket_id = 'partidas' and (storage.foldername(name))[1] = public.mi_pareja()::text);

-- ---------- Tiempo real ----------
alter publication supabase_realtime add table public.mensajes, public.invitaciones, public.partidas, public.juegos;
