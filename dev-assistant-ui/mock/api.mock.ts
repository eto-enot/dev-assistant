import { ServerResponse, IncomingMessage } from 'http';
import { defineMock, Method } from 'vite-plugin-mock-dev-server';

const setProjectInfoMock = {
    url: '/set-project-info',
    method: 'POST' as Method,
    response(_req: IncomingMessage, res: ServerResponse) {
        res.statusCode = 200;
        res.end();
    },
};

const reindexProjectMock = {
    url: '/reindex',
    method: 'POST' as Method,
    response(_req: IncomingMessage, res: ServerResponse) {
        res.statusCode = 200;
        res.end();
    },
};

export default defineMock([setProjectInfoMock, reindexProjectMock]);
