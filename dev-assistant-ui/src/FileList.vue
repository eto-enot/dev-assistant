<script setup lang="ts">
import { inject, onMounted, reactive, watch, type Ref } from 'vue';
import type { ListFilesRequest, ListFilesResponse, Settings } from './types';

const emit = defineEmits(['file-selected'])
const model = defineModel<string>();
const files = reactive([] as ListFilesResponse);

const settings = inject<Ref<Settings>>('Settings');
let curDirectory = settings?.value.currentDirectory?.trim() ?? '.';

onMounted(async () => {
    await updateFiles();
    watch(model, updateFiles);
});

async function updateFiles() {
    try {
        const response = await fetch('/list-files', {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(<ListFilesRequest>{
                filter: (model.value ?? '').substring(1),
                work_directory: curDirectory,
            }),
        });

        if (!response.ok)
            throw new Error(`Error: ${response.status} ${response.statusText}`);

        files.splice(0, files.length);
        files.push(...await response.json());
    } catch (e) {
        console.error(e);
    }
}

async function onClick(file: { name: string; path: string }) {
    if (file.name.endsWith('/')) {
        if (!curDirectory.endsWith('/'))
            curDirectory += '/';
        curDirectory += file.name;
        await updateFiles();
    } else {
        emit('file-selected', file.path);
    }
}
</script>

<template>
    <div class="file-list">
        <div class="file-list-content">
            <datalist style="display: block;" v-for="item in files" :key="item.name">
                <option :value="item.path" @click="() => onClick(item)">{{ item.name }}</option>
            </datalist>
        </div>
    </div>
</template>

<style lang="css" scoped>
.file-list {
    position: absolute;
    bottom: 8rem;
    width: 100%;
}

.file-list-content {
    position: relative;
    max-width: 768px;
    margin-left: -408px;
    left: 50%;
    padding: .25rem;
    border: 2px solid whitesmoke;
    max-height: 16rem;
    overflow: auto;
}

datalist > option {
    cursor: pointer;
}

datalist > option:hover {
    background-color: whitesmoke;
    color: black;
}
</style>
