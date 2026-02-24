export interface Template {
  id: string;
  name: string;
  content: string[];
  is_default: boolean;
  created_at: string;
}

export interface TaskStatistics {
  total: number;
  done: number;
  failed: number;
  skipped: number;
  queued: number;
  processing: number;
}

export interface Task {
  id: string;
  name: string;
  description?: string;
  template_id: string;
  model_name?: string;
  status: string;
  created_at: string;
  updated_at: string;
  statistics?: TaskStatistics;
}

export interface Paper {
  id: string;
  task_id: string;
  title: string;
  pdf_path?: string;
  source?: string;
  source_url?: string;
  status: string;
  failure_reason?: string;
  created_at: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  cost?: number;
  time_cost?: number;
  created_at?: string;
}

export interface Note {
  content: string;
}

export interface Collection {
  id: string;
  name: string;
  parent_id?: string;
}

export interface CreateTaskPayload {
  name: string;
  description?: string;
  template_id: string;
  model_name?: string;
}

export interface CreateTemplatePayload {
  name: string;
  content: string[];
  is_default?: boolean;
}

export interface AddPapersPayload {
  titles: string[];
}
