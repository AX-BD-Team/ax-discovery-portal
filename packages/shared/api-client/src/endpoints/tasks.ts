import { apiClient } from '../client'

/**
 * Task 상태
 */
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked'

/**
 * Task 우선순위
 */
export type TaskPriority = 'P0' | 'P1' | 'P2'

/**
 * Task 응답
 */
export interface Task {
  task_id: string
  play_id: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  assignee?: string
  due_date?: string
  completed_at?: string
  order_index: number
  source_text?: string
  blocker_note?: string
  created_at?: string
  updated_at?: string
}

/**
 * Task 목록 응답
 */
export interface TaskListResponse {
  items: Task[]
  total: number
}

/**
 * Task 통계 응답
 */
export interface TaskStats {
  total: number
  completed: number
  in_progress: number
  pending: number
  blocked: number
  completion_rate: number
}

/**
 * Task 생성 요청
 */
export interface CreateTaskRequest {
  play_id: string
  title: string
  description?: string
  priority?: TaskPriority
  assignee?: string
  due_date?: string
}

/**
 * Task 업데이트 요청
 */
export interface UpdateTaskRequest {
  title?: string
  description?: string
  priority?: TaskPriority
  assignee?: string
  due_date?: string
  status?: TaskStatus
  blocker_note?: string
}

/**
 * Task 자동 생성 응답
 */
export interface GenerateTasksResponse {
  play_id: string
  tasks_created: number
  tasks: Task[]
}

/**
 * Task API endpoints
 */
export const tasksApi = {
  /**
   * Task 목록 조회
   */
  async getTasks(params?: { play_id?: string; status?: TaskStatus }): Promise<TaskListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.play_id) searchParams.append('play_id', params.play_id)
    if (params?.status) searchParams.append('status', params.status)

    const query = searchParams.toString()
    return apiClient.get(`api/tasks${query ? `?${query}` : ''}`).json<TaskListResponse>()
  },

  /**
   * 미완료 Task 목록 조회
   */
  async getPendingTasks(params?: { play_id?: string; limit?: number }): Promise<TaskListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.play_id) searchParams.append('play_id', params.play_id)
    if (params?.limit) searchParams.append('limit', params.limit.toString())

    const query = searchParams.toString()
    return apiClient.get(`api/tasks/pending${query ? `?${query}` : ''}`).json<TaskListResponse>()
  },

  /**
   * 기한 초과 Task 목록 조회
   */
  async getOverdueTasks(): Promise<TaskListResponse> {
    return apiClient.get('api/tasks/overdue').json<TaskListResponse>()
  },

  /**
   * 블로킹된 Task 목록 조회
   */
  async getBlockedTasks(): Promise<TaskListResponse> {
    return apiClient.get('api/tasks/blocked').json<TaskListResponse>()
  },

  /**
   * Task 상세 조회
   */
  async getTask(taskId: string): Promise<Task> {
    return apiClient.get(`api/tasks/${taskId}`).json<Task>()
  },

  /**
   * Task 생성
   */
  async createTask(request: CreateTaskRequest): Promise<Task> {
    return apiClient.post('api/tasks', { json: request }).json<Task>()
  },

  /**
   * Task 업데이트
   */
  async updateTask(taskId: string, request: UpdateTaskRequest): Promise<Task> {
    return apiClient.patch(`api/tasks/${taskId}`, { json: request }).json<Task>()
  },

  /**
   * Task 완료 처리
   */
  async completeTask(taskId: string): Promise<Task> {
    return apiClient.post(`api/tasks/${taskId}/complete`).json<Task>()
  },

  /**
   * Task 시작 처리
   */
  async startTask(taskId: string): Promise<Task> {
    return apiClient.post(`api/tasks/${taskId}/start`).json<Task>()
  },

  /**
   * Task 블로킹 처리
   */
  async blockTask(taskId: string, blockerNote?: string): Promise<Task> {
    const searchParams = new URLSearchParams()
    if (blockerNote) searchParams.append('blocker_note', blockerNote)
    const query = searchParams.toString()
    return apiClient.post(`api/tasks/${taskId}/block${query ? `?${query}` : ''}`).json<Task>()
  },

  /**
   * Task 삭제
   */
  async deleteTask(taskId: string): Promise<{ status: string; task_id: string }> {
    return apiClient.delete(`api/tasks/${taskId}`).json()
  },

  /**
   * Play에서 Task 자동 생성
   */
  async generateTasks(params: {
    play_id: string
    include_goal_tasks?: boolean
    due_date?: string
  }): Promise<GenerateTasksResponse> {
    return apiClient.post('api/tasks/generate', { json: params }).json<GenerateTasksResponse>()
  },

  /**
   * Play별 Task 통계 조회
   */
  async getTaskStats(playId: string): Promise<TaskStats & { play_id: string; play_name: string }> {
    return apiClient.get(`api/tasks/stats/${playId}`).json()
  },
}
