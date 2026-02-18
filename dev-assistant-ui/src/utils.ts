import type { Role, Settings } from './types';

export const DEFAULT_SETTINGS: Settings = {
    apiUrl: 'http://localhost:5002/v1/chat/completions'
}

export function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
}

type MessageUpdatedCallback = (messageId: string, accumulatedText: string) => void;

// process streaming response frmo model
export async function processStreamResponse(response: Response, messageId: string, messageUpdatedCallback: MessageUpdatedCallback) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedText = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done)
            break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

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
                const parsed = JSON.parse(data);
                const content = parsed.choices[0]?.delta?.content || '';

                if (content) {
                    accumulatedText += content;
                    messageUpdatedCallback(messageId, accumulatedText);
                }
            } catch (e) {
                console.error('Error parsing stream data:', e);
            }
        }
    }
}

export function escapeHtml(text: string) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function renderMarkdown(text: string) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');

    // Code blocks with language detection
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, function (match, lang, code) {
        const language = lang || 'plaintext';
        const escapedCode = escapeHtml(code.trim());
        return `<div class="code-block-wrapper"><button class="copy-code-btn" @click="copyCodeToClipboard">Copy</button><pre><code class="language-${language}">${escapedCode}</code></pre></div>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes
    html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Lists (unordered)
    html = html.replace(/^\s*[-*+] (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/g, '<ul>$1</ul>');

    // Lists (ordered)
    html = html.replace(/^\s*\d+\. (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/g, '<ol>$1</ol>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Horizontal rule
    html = html.replace(/^---$/gim, '<hr>');

    // Tables (simple support)
    html = html.replace(/\|(.+)\|/g, function (match, row) {
        const cells = row.split('|').map(cell => cell.trim());
        if (cells.some(cell => cell.includes('---'))) {
            return ''; // Skip separator rows for now
        }
        const cellTags = cells.map(cell => `<td>${cell}</td>`).join('');
        return `<tr>${cellTags}</tr>`;
    });

    // Wrap table rows in table tags
    const tableRows = html.match(/<tr>.*?<\/tr>/g);
    if (tableRows && tableRows.length > 0) {
        const tableHeader = '<table><thead><tr><th>Column 1</th><th>Column 2</th></tr></thead><tbody>';
        const tableFooter = '</tbody></table>';
        html = html.replace(/(<tr>.*?<\/tr>)/g, tableHeader + tableRows.join('') + tableFooter);
    }

    // Paragraphs (ensure proper wrapping)
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/<p><\/p>/g, '');

    // Handle line breaks
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph tags if not already wrapped
    if (!html.startsWith('<') || html.startsWith('<br>')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

export class Message {

    public readonly id: string;
    public readonly role: Role;

    public content: string;

    constructor (id: string, role: Role, content: string) {
        this.id = id;
        this.role = role;
        this.content = content;
    }

    get avatarIcon() {
        return this.role === 'user' ? 'fas fa-user' : 'fas fa-robot';
    }

    get isThinking() {
        return this.role === 'assistant' && !this.content;
    }

    get contentHtml() {
        return this.content
            ? renderMarkdown(this.content)
            : (this.role === 'user' ? escapeHtml(this.content) : '');
    }
}
