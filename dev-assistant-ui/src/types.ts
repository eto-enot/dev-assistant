export type Role = 'user' | 'assistant';

export interface HistoryMessage {
    role: Role;
    content: string;
    timestamp: number;
}

export interface HistoryChat {
    id: string;
    timestamp: number;
    messages: HistoryMessage[];
}

export interface Conversations {
    [id: string]: HistoryChat;
}

export interface Settings {
    model: string;
    apiUrl: string;
    currentDirectory: string;
    coreInfo: string;
}

export interface SetProjectInfoRequest {
    session_id: string;
    work_directory: string;
    core_info: string;
}
