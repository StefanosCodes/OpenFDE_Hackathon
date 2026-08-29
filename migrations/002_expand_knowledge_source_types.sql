ALTER TABLE knowledge_sources
DROP CONSTRAINT IF EXISTS knowledge_sources_source_type_check;

ALTER TABLE knowledge_sources
ADD CONSTRAINT knowledge_sources_source_type_check
CHECK (source_type IN (
    'markdown', 'pdf', 'url', 'text', 'csv', 'word', 'excel',
    'powerpoint', 'audio', 'image'
));
