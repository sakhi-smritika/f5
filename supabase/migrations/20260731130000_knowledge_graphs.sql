-- User-managed knowledge graphs for concept-based kbit generation.

create table public.knowledge_graphs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index knowledge_graphs_user_id_idx on public.knowledge_graphs (user_id);

create table public.knowledge_nodes (
  id uuid primary key default gen_random_uuid(),
  graph_id uuid not null references public.knowledge_graphs (id) on delete cascade,
  label text not null,
  description text,
  user_interest real not null default 0,
  kbit_count integer not null default 0,
  last_expanded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index knowledge_nodes_graph_id_label_lower_idx
  on public.knowledge_nodes (graph_id, lower(label));

create index knowledge_nodes_graph_id_idx on public.knowledge_nodes (graph_id);

create table public.knowledge_edges (
  id uuid primary key default gen_random_uuid(),
  graph_id uuid not null references public.knowledge_graphs (id) on delete cascade,
  source_id uuid not null references public.knowledge_nodes (id) on delete cascade,
  target_id uuid not null references public.knowledge_nodes (id) on delete cascade,
  relationship text not null default 'related',
  created_at timestamptz not null default now(),
  unique (graph_id, source_id, target_id),
  check (source_id < target_id)
);

create index knowledge_edges_graph_id_idx on public.knowledge_edges (graph_id);

create table public.knowledge_bit_nodes (
  kbit_id uuid not null references public.knowledge_bits (id) on delete cascade,
  node_id uuid not null references public.knowledge_nodes (id) on delete cascade,
  primary key (kbit_id, node_id)
);

create index knowledge_bit_nodes_node_id_idx on public.knowledge_bit_nodes (node_id);

alter table public.knowledge_bits
  add column if not exists metadata jsonb;

comment on column public.knowledge_bits.metadata is
  'Structured provenance for graph-based generation (strategies, graph, node, new concepts).';

-- updated_at triggers (reuse goals pattern)

create or replace function public.set_knowledge_graphs_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger knowledge_graphs_set_updated_at
  before update on public.knowledge_graphs
  for each row
  execute function public.set_knowledge_graphs_updated_at();

create or replace function public.set_knowledge_nodes_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger knowledge_nodes_set_updated_at
  before update on public.knowledge_nodes
  for each row
  execute function public.set_knowledge_nodes_updated_at();

-- RLS

alter table public.knowledge_graphs enable row level security;
alter table public.knowledge_nodes enable row level security;
alter table public.knowledge_edges enable row level security;
alter table public.knowledge_bit_nodes enable row level security;

create policy "Users can view their own knowledge graphs"
  on public.knowledge_graphs for select
  using (auth.uid() = user_id);

create policy "Users can insert their own knowledge graphs"
  on public.knowledge_graphs for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own knowledge graphs"
  on public.knowledge_graphs for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete their own knowledge graphs"
  on public.knowledge_graphs for delete
  using (auth.uid() = user_id);

create policy "Users can view nodes in their graphs"
  on public.knowledge_nodes for select
  using (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can insert nodes in their graphs"
  on public.knowledge_nodes for insert
  with check (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can update nodes in their graphs"
  on public.knowledge_nodes for update
  using (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can delete nodes in their graphs"
  on public.knowledge_nodes for delete
  using (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can view edges in their graphs"
  on public.knowledge_edges for select
  using (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can insert edges in their graphs"
  on public.knowledge_edges for insert
  with check (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can delete edges in their graphs"
  on public.knowledge_edges for delete
  using (
    exists (
      select 1 from public.knowledge_graphs g
      where g.id = graph_id and g.user_id = auth.uid()
    )
  );

create policy "Users can view bit-node links for their bits"
  on public.knowledge_bit_nodes for select
  using (
    exists (
      select 1 from public.knowledge_bits b
      where b.id = kbit_id and b.user_id = auth.uid()
    )
  );

create policy "Users can insert bit-node links for their bits"
  on public.knowledge_bit_nodes for insert
  with check (
    exists (
      select 1 from public.knowledge_bits b
      where b.id = kbit_id and b.user_id = auth.uid()
    )
  );
