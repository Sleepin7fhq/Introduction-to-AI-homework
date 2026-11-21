import type { RenderStage } from '../engine/backends';

export interface ProducerMessage {
  id: number;
  role: 'user' | 'producer';
  text: string;
  bullets?: string[];
  meta?: string;
}

export interface TaskState {
  running: boolean;
  label: string;
  stages: RenderStage[];
  error?: string;
}
