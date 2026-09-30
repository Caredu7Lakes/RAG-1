CREATE TABLE setor (
    id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome  TEXT NOT NULL UNIQUE
);

-- Identidade vem do Entra ID (OIDC). Senha NUNCA aqui.
CREATE TABLE usuario (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sso_subject  TEXT NOT NULL UNIQUE,           -- 'sub' do token OIDC (Entra ID)
    email        TEXT NOT NULL UNIQUE,
    setor_id     BIGINT NOT NULL REFERENCES setor(id),
    ativo        BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE grupo (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fonte      TEXT NOT NULL,                     -- 'entra' | 'sharepoint' | 'teams' | 'regulado'
    fonte_ref  TEXT NOT NULL,
    nome       TEXT,
    UNIQUE (fonte, fonte_ref)
);

CREATE TABLE grupo_membro (
    grupo_id    BIGINT NOT NULL REFERENCES grupo(id),
    usuario_id  BIGINT NOT NULL REFERENCES usuario(id),
    PRIMARY KEY (grupo_id, usuario_id)
);

CREATE TABLE documento (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fonte         TEXT NOT NULL,                  -- 'sharepoint' | 'onedrive' | 'teams' | 'regulado'
    fonte_ref     TEXT NOT NULL,
    tipo          TEXT NOT NULL,                  -- 'tabela' | 'pdf' | 'docx' | 'imagem' | 'texto'
    setor_id      BIGINT NOT NULL REFERENCES setor(id),
    uri           TEXT,                           -- ponteiro para o Blob Storage
    -- Atributos ABAC do setor regulado (nulos fora dele):
    estudo_ref    TEXT,
    blinding      TEXT,                           -- 'blinded' | 'unblinded' | NULL
    sponsor_ref   TEXT,
    atualizado_em TIMESTAMPTZ NOT NULL,
    UNIQUE (fonte, fonte_ref)
);

-- ACL RESOLVIDA (replicada para o índice como metadado de pré-filtro)
CREATE TABLE documento_acl (
    documento_id    BIGINT NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
    principal_tipo  TEXT NOT NULL,                -- 'usuario' | 'grupo' | 'especial'
    principal_ref   TEXT NOT NULL,                -- id do usuario/grupo, ou 'tenant:all'/'sector:<id>'/'team:<id>'
    PRIMARY KEY (documento_id, principal_tipo, principal_ref)
);
CREATE INDEX idx_acl_principal ON documento_acl (principal_tipo, principal_ref);

CREATE TABLE chunk (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    documento_id  BIGINT NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
    ordem         INT NOT NULL,
    conteudo      TEXT,                           -- vetor referenciado por este id no Azure AI Search
    UNIQUE (documento_id, ordem)
);

CREATE TABLE auditoria (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  BIGINT REFERENCES usuario(id),
    pergunta    TEXT NOT NULL,
    fontes_ret  TEXT[],
    resultado   TEXT NOT NULL,                    -- 'ok' | 'nao_encontrado' | 'negado'
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Log de propostas de atualização de documento (gate humano + padrão).
-- Um registro por desfecho: rejeitado_padrao | aprovado | rejeitado_humano.
CREATE TABLE auditoria_atualizacao (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    documento_id   BIGINT NOT NULL REFERENCES documento(id),
    proposto_por   TEXT NOT NULL,                 -- sso_subject de quem propôs
    aprovado_por   TEXT,                          -- sso_subject de quem aprovou/rejeitou; NULL se reprovado no padrão
    desfecho       TEXT NOT NULL,                 -- 'rejeitado_padrao' | 'aprovado' | 'rejeitado_humano'
    motivo         TEXT NOT NULL,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    reingerido_em  TIMESTAMPTZ                     -- quando o job noturno aplicou; NULL = pendente
);
-- Segregação de função: quem propõe não aprova (reforço no app; constraint documenta a intenção)
CREATE INDEX idx_auditoria_pendente_reingest
    ON auditoria_atualizacao (desfecho, reingerido_em)
    WHERE desfecho = 'aprovado' AND reingerido_em IS NULL;
