export interface User {
  id: string;
  email: string;
  name: string;
  company: string | null;
  job_title: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserUpdateRequest {
  name?: string;
  company?: string;
  job_title?: string;
  current_password?: string;
  new_password?: string;
}
