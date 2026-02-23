import { Marked } from "marked";
import { AnswerMessageUpdateEvent, ErrorMessageUpdateEvent, ReasoningMessageUpdateEvent, ToolCallConfirmMessageUpdateEvent, ToolCallMessageUpdateEvent, type MessageUpdateEvent } from "./events";
import type { Role } from "./types";
import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js';

function escapeHtml(text: string) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const marked = new Marked(
    markedHighlight({
        emptyLangClass: 'hljs',
        langPrefix: 'hljs language-',
        highlight(code, lang, _info) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        }
    })
);

function renderMarkdown(text: string) {
    if (!text) return '';

    text = text.replace(/Thought:/gm, '\n**Thought:**');
    text = text.replace(/Action:/gm, '\n**Action:**');
    text = text.replace(/Answer:/gm, '\n**Answer:**');
    text = text.replace(/Action Input:/gm, '\n**Action Input:**');
    text = text.replace(/Tool Call:/gm, '\n**Tool Call:**');

    return marked.parse(text);
}

export class Message {

    public readonly id: string;
    public readonly role: Role;
    public content: string;
    public reasoning = '';
    public isError = false;
    public isReasoningCollapsed = true;
    public toolConfirmRequested = false;
    public toolConfirmMessage = '';

    constructor(id: string, role: Role, content: string) {
        this.id = id;
        this.role = role;
        this.content = content;
    }

    update(event: MessageUpdateEvent) {
        if (event instanceof ErrorMessageUpdateEvent) {
            this.isError = true;
            this.reasoning = '';
            this.content = this.content;
        } else if (event instanceof ReasoningMessageUpdateEvent) {
            this.reasoning += event.content;
        } else if (event instanceof AnswerMessageUpdateEvent) {
            this.content += event.content;
        } else if (event instanceof ToolCallMessageUpdateEvent) {
            if (!this.reasoning.endsWith(event.content + '\n'))
                this.reasoning += '\n' + event.content + '\n';
        } else if (event instanceof ToolCallConfirmMessageUpdateEvent) {
            this.toolConfirmRequested = true;
            this.toolConfirmMessage = event.content;
        } else {
            throw new Error('Unknown event type: ' + event.constructor);
        }
    }

    confirm(isAllowed: boolean) {
        this.toolConfirmRequested = false;
        this.toolConfirmMessage = '';
    }

    get avatarIcon() {
        return this.role === 'user' ? 'fas fa-user' : 'fas fa-robot';
    }

    get isThinking() {
        return this.role === 'assistant' && !this.content;
    }

    get reasoningHtml() {
        return renderMarkdown(this.reasoning);
    }

    get contentHtml() {
        if (this.isError)
            return escapeHtml(this.content);

        return marked.parse(this.content);
    }
}
