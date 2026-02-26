export type Role = 'system' | 'user' | 'assistant' | 'tool';

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
    os: string;
}

export interface ConfirmToolCallRequest {
    session_id: string;
    call_allowed: boolean;
}

export interface ChatCompletionError {
    error: ChatCompletionErrorInfo;
}

export interface ChatCompletionErrorInfo {
    message: string;
    type: string;
    code: string;
}

export interface ChatCompletionChunk {
    id: string;
    object: 'chat.completion.chunk';
    created: number;
    model: string;
    type: 'reasoning' | 'tool_call' | 'tool_call_result' | 'tool_call_confirm' | 'answer';
    choices: ChatCompletionStreamingChoice[];
}

export interface ChatCompletionStreamingChoice {
    index: number;
    finish_reason: string;
    delta: ChoiceDelta;
}

export interface ChoiceDelta {
    role: Role;
    content: string;
    tool_call_id?: string;
    tool_calls?: ToolCall[];
}

export interface ToolCall {
    id: string;
    type: 'function';
    function: FunctionCall;
}

export interface FunctionCall {
    name: string;
    arguments: string;
}
