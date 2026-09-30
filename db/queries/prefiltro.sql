-- Pré-filtro / reconciliação (fonte de verdade: PostgreSQL)
-- Versão indexável: compara (principal_tipo, principal_ref) como PARES,
-- usando idx_acl_principal (principal_tipo, principal_ref).
-- NÃO concatena em tempo de query (concatenar impede o índice).
--
-- Parâmetros:
--   $1 = principal_tipos[]   ex.: ARRAY['grupo','especial','especial']
--   $2 = principal_refs[]    ex.: ARRAY['7','sector:3','tenant:all']
--        ($1[i], $2[i]) formam o i-ésimo par; os dois arrays têm o mesmo tamanho.
--   $3 = usuario_blinded_em[]  estudos onde o usuário é blinded
--   $4 = candidatos[]          ids de chunk vindos do índice/grafo

SELECT c.id, c.documento_id, c.ordem
FROM chunk c
JOIN documento d       ON d.id = c.documento_id
JOIN documento_acl acl ON acl.documento_id = d.id
-- pares do usuário desempacotados em linhas; casa com o índice composto
JOIN unnest($1::text[], $2::text[]) AS u(principal_tipo, principal_ref)
     ON acl.principal_tipo = u.principal_tipo
    AND acl.principal_ref  = u.principal_ref
WHERE NOT (d.blinding = 'unblinded' AND d.estudo_ref = ANY ($3))  -- barra unblinded p/ blinded
  AND c.id = ANY ($4)                                             -- candidatos do índice/grafo
GROUP BY c.id, c.documento_id, c.ordem;                           -- dedup: doc visível por >1 principal
