import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";

export interface DocumentQuizQuestion {
  question: string;
  options?: string[] | null;
  answer: string;
  explanation?: string | null;
  question_type: string;
}

export interface DocumentQuizResponse {
  source: string;
  questions: DocumentQuizQuestion[];
  title: string;
  description: string;
  quiz_id?: string;
  live_quiz_enabled?: boolean;
  access_code?: string | null;
  time_limit_minutes?: number | null;
  access_code_expires_at?: string | null;
  source_document_type: string;
  source_document_name: string;
  source_characters: number;
  total_source_chunks: number;
  retrieved_chunks: number;
  retrieval_query: string;
  rag_strategy?: string;
  embedding_cache_hit?: boolean;
}

export async function generateDocumentQuiz(
  payload: FormData,
  options?: { authenticated?: boolean },
): Promise<DocumentQuizResponse> {
  const client = options?.authenticated ? api : publicApi;
  const response = await client.post(
    "/api/document-quizzes/generate",
    payload,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return response.data as DocumentQuizResponse;
}
