import { AnswerMessageUpdateEvent, ErrorMessageUpdateEvent, MessageUpdateEvent, ReasoningMessageUpdateEvent, ToolCallConfirmMessageUpdateEvent, ToolCallMessageUpdateEvent, ToolCallResultMessageUpdateEvent } from './events';
import type { ChatCompletionChunk, ChatCompletionError, FunctionCall, Settings } from './types';

export function getOS() {
    const platform = window.navigator.platform || window.navigator.userAgentData?.platform;
    return (platform?.indexOf('Win') ?? -1) >= 0 ? 'Windows' : 'Linux';
}

function getCurrentDirectory() {
    const isWindows = getOS() === 'Windows';
    const idx = window.location.pathname.lastIndexOf('/');
    return window.location.pathname.substring(isWindows ? 1 : 0, idx);
}

export function getDefaultSettings() {
    return <Settings>{
        model: 'Coder LLM',
        apiUrl: 'http://localhost:8000',
        currentDirectory: getCurrentDirectory(),
        coreInfo: '',
    };
}

export function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
}

type MessageUpdatedCallback = (messageId: string, event: MessageUpdateEvent) => void;

// process streaming response frmo model
export async function processStreamResponse(response: Response, messageId: string, messageUpdatedCallback: MessageUpdatedCallback) {
    const reader = response.body?.getReader();
    if (!reader)
        throw new Error('Unable to read the response');

    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done)
            break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');
        let callInfo: FunctionCall | undefined;

        for (const line of lines) {
            // skip non-data lines
            if (!line.startsWith('data: '))
                continue;

            // remove 'data: ' substring
            const data = line.substring(6);

            // skip [DONE] message
            if (data === '[DONE]')
                continue;

            try {
                const parsed: ChatCompletionChunk | ChatCompletionError = JSON.parse(data);
                if ('error' in parsed) {
                    messageUpdatedCallback(messageId, new ErrorMessageUpdateEvent(`Error: ${parsed.error.message}`));
                } else {
                    const choice = parsed.choices[0];
                    const content = choice?.delta?.content ?? '';

                    let event: MessageUpdateEvent | undefined;
                    switch (parsed.type) {
                        case 'answer':
                            if (!content)
                                continue;
                            event = new AnswerMessageUpdateEvent(content);
                            break;
                        case 'reasoning':
                            if (!content)
                                continue;
                            event = new ReasoningMessageUpdateEvent(content);
                            break;
                        case 'tool_call':
                            callInfo = choice?.delta.tool_calls![0]?.function;
                            const text = `Tool Call: ${callInfo?.name}\n`;
                            event = new ToolCallMessageUpdateEvent(text);
                            break;
                        case 'tool_call_result':
                            event = new ToolCallResultMessageUpdateEvent(`Tool Call Result: ${content}\n`);
                            break;
                        case 'tool_call_confirm':
                            event = new ToolCallConfirmMessageUpdateEvent(content);
                            break;
                        default:
                            throw new Error('Unknown message type: ' + parsed.type);
                    }

                    if (event)
                        messageUpdatedCallback(messageId, event);
                }
            } catch (e) {
                console.error('Error parsing stream data:', e);
            }
        }
    }
}
