/* eslint-disable @typescript-eslint/no-explicit-any */

import { ServerResponse } from 'http';
import { defineMock, Method } from 'vite-plugin-mock-dev-server';

const setProjectInfoMock = {
    url: '/set-project-info',
    method: 'POST' as Method,
    response(_req: any, res: ServerResponse) {
        res.statusCode = 200;
        res.end();
    },
};

const reindexProjectMock = {
    url: '/reindex',
    method: 'POST' as Method,
    response(_req: any, res: ServerResponse) {
        res.statusCode = 200;
        res.end();
    },
};

const listFilesMock = {
    url: '/list-files',
    method: 'POST' as Method,
    response(req: any, res: ServerResponse) {
        let body: any[];
        const dir: string = req.body.work_directory;
        if (dir.indexOf('src') >= 0) {
            body = [
                { name: 'assets/', path: 'src/assets/', },
                { name: 'additional.d.ts', path: 'src/additional.d.ts', },
                { name: 'App.vue', path: 'src/App.vue', },
                { name: 'chat.ts', path: 'src/chat.ts', },
                { name: 'debounce.ts', path: 'src/debounce.ts', },
                { name: 'events.ts', path: 'src/events.ts', },
                { name: 'FileList.vue', path: 'src/FileList.vue', },
                { name: 'main.ts', path: 'src/main.ts', },
                { name: 'Messages.vue', path: 'src/Messages.vue', },
                { name: 'Prompt.vue', path: 'src/Prompt.vue', },
                { name: 'Settings.vue', path: 'src/Settings.vue', },
                { name: 'types.ts', path: 'src/types.ts', },
                { name: 'utils.ts', path: 'src/utils.ts', },
            ];
        } else {
            body = [
                { name: '.vscode/', path: '.vscode/', },
                { name: 'dist/', path: 'dist/', },
                { name: 'mock/', path: 'mock/', },
                { name: 'node_modules/', path: 'node_modules/', },
                { name: 'src/', path: 'src/', },
                { name: '.editorconfig', path: '.editorconfig', },
                { name: '.gitattributes', path: '.gitattributes', },
                { name: '.gitignore', path: '.gitignore', },
                { name: '.oxlintrc.json', path: '.oxlintrc.json', },
                { name: '.prettierrc.json', path: '.prettierrc.json', },
                { name: 'chat.html', path: 'chat.html', },
                { name: 'env.d.ts', path: 'env.d.ts', },
                { name: 'eslint.config.ts', path: 'eslint.config.ts', },
                { name: 'package.json', path: 'package.json', },
                { name: 'package-lock.json', path: 'package-lock.json', },
                { name: 'tsconfig.json', path: 'tsconfig.json', },
                { name: 'tsconfig.app.json', path: 'tsconfig.app.json', },
                { name: 'tsconfig.node.json', path: 'tsconfig.node.json', },
                { name: 'vite.config.ts', path: 'vite.config.ts', },
            ];
        }
        res.statusCode = 200;
        res.end(JSON.stringify(body));
    },
    /*body: */
};

export default defineMock([setProjectInfoMock, reindexProjectMock, listFilesMock]);
