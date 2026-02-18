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
    apiUrl: string;
}
