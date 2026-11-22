-- Triagem pelo coordenador (ticket 08): quem decidiu, quando, e justificativa da troca de tier.

ALTER TABLE candidatos
  ADD COLUMN decidido_por       uuid REFERENCES perfis(usuario_id),
  ADD COLUMN decidido_em        timestamptz,
  ADD COLUMN justificativa_tier text,
  ADD CONSTRAINT troca_de_tier_justificada
    CHECK (tier_final IS NULL OR length(trim(justificativa_tier)) > 0);
