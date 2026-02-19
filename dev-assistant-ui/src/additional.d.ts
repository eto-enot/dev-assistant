declare interface Navigator extends NavigatorUA {}

declare interface NavigatorUA {
    readonly userAgentData?: NavigatorUAData;
}

interface NavigatorUAData {
    readonly platform: string;
}
