from elasticsearch import AsyncElasticsearch
from core.config import settings

elastic_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)