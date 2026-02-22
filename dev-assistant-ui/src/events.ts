export abstract class MessageUpdateEvent {
    constructor(public content = '') {

    }
}

export class ReasoningMessageUpdateEvent extends MessageUpdateEvent {
    constructor(content: string) {
        super(content);
    }
}

export class AnswerMessageUpdateEvent extends MessageUpdateEvent {
    constructor(content: string) {
        super(content);
    }
}

export class ToolCallMessageUpdateEvent extends MessageUpdateEvent {
    constructor(content: string) {
        super(content);
    }
}

export class ErrorMessageUpdateEvent extends MessageUpdateEvent {
    constructor(content: string) {
        super(content);
    }
}
