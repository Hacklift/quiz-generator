import publicApi from "@shared/api/publicHttp";
import type {
  StartedTrainingSession,
  TrainingAccessPreview,
} from "./trainingRunApi";

export const trainingAccessApi = {
  async preview(code: string): Promise<TrainingAccessPreview> {
    const { data } = await publicApi.get(
      `/api/v1/training-runs/access/${encodeURIComponent(code.trim().toUpperCase())}`,
    );
    return data;
  },

  async start(payload: {
    code: string;
    participant_name: string;
    participant_email?: string;
  }): Promise<StartedTrainingSession> {
    const { code, ...body } = payload;
    const { data } = await publicApi.post(
      `/api/v1/training-runs/access/${encodeURIComponent(code.trim().toUpperCase())}/start`,
      body,
    );
    return data;
  },
};
