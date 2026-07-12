import publicApi from "@shared/api/publicHttp";

export interface CategoryQuestion {
  question: string;
  options?: string[] | null;
  correct_answer?: string;
  answer?: string;
  question_type?: string;
  category?: string;
  subcategory?: string;
  quiz_id?: string;
  title?: string;
}

export const getCategories = async (): Promise<string[]> => {
  const { data } = await publicApi.get("/api/categories");
  return data;
};

export const getSubcategories = async (category: string): Promise<string[]> => {
  const { data } = await publicApi.get(
    `/api/category/${encodeURIComponent(category)}/subcategories`,
  );
  return data;
};

export const getCategoryQuizTypes = async (
  category: string,
  subcategory: string,
): Promise<string[]> => {
  const { data } = await publicApi.get(
    `/api/category/${encodeURIComponent(category)}/subcategory/${encodeURIComponent(subcategory)}/types`,
  );
  return data;
};

export const getCategoryQuestions = async ({
  category,
  subcategory,
  questionType,
  page = 1,
  pageSize = 10,
}: {
  category: string;
  subcategory: string;
  questionType: string;
  page?: number;
  pageSize?: number;
}): Promise<CategoryQuestion[]> => {
  const { data } = await publicApi.get(
    `/api/category/${encodeURIComponent(category)}/subcategory/${encodeURIComponent(subcategory)}/type/${encodeURIComponent(questionType)}`,
    {
      params: {
        page,
        page_size: pageSize,
      },
    },
  );
  return data;
};
