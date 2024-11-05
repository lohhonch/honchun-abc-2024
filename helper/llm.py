import tiktoken
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from helper.utility import get_secret_value

model_name = get_secret_value("OPENAI_MODEL_NAME")
embeddings_model = OpenAIEmbeddings(model=get_secret_value("EMBEDDINGS_MODEL"))
llm = ChatOpenAI(model=model_name, temperature=0, seed=42)


def count_tokens(text):
  encoding = tiktoken.encoding_for_model(model_name)
  return len(encoding.encode(text))
