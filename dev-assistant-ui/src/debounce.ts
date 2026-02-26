/* eslint-disable @typescript-eslint/no-explicit-any */

// from https://github.com/vueuse/vueuse project

import { ref, shallowReadonly, toValue, watch, type MaybeRefOrGetter, type Ref } from "vue"

export type ArgumentsType<T> = T extends (...args: infer U) => any ? U : never
export type AnyFn = (...args: any[]) => any
export type FunctionArgs<Args extends any[] = any[], Return = unknown> = (...args: Args) => Return
export type Promisify<T> = Promise<Awaited<T>>
export type PromisifyFn<T extends AnyFn> = (...args: ArgumentsType<T>) => Promisify<ReturnType<T>>
export type UseDebounceFnReturn<T extends FunctionArgs> = PromisifyFn<T>
export type TimerHandle = ReturnType<typeof setTimeout> | undefined
export type RefDebouncedReturn<T = any> = Readonly<Ref<T>>

const noop = () => { }

export interface FunctionWrapperOptions<Args extends any[] = any[], This = any> {
    fn: FunctionArgs<Args, This>
    args: Args
    thisArg: This
}

export type EventFilter<Args extends any[] = any[], This = any, Invoke extends AnyFn = AnyFn> = (
    invoke: Invoke,
    options: FunctionWrapperOptions<Args, This>,
) => ReturnType<Invoke> | Promisify<ReturnType<Invoke>>

export interface DebounceFilterOptions {
    /**
     * The maximum time allowed to be delayed before it's invoked.
     * In milliseconds.
     */
    maxWait?: MaybeRefOrGetter<number>

    /**
     * Whether to reject the last call if it's been cancel.
     *
     * @default false
     */
    rejectOnCancel?: boolean
}

export function createFilterWrapper<T extends AnyFn>(filter: EventFilter, fn: T) {
    function wrapper(this: any, ...args: ArgumentsType<T>) {
        return new Promise<Awaited<ReturnType<T>>>((resolve, reject) => {
            // make sure it's a promise
            Promise.resolve(filter(() => fn.apply(this, args), { fn, thisArg: this, args }))
                .then(resolve)
                .catch(reject)
        })
    }

    return wrapper
}

export function useDebounceFn<T extends FunctionArgs>(
    fn: T,
    ms: MaybeRefOrGetter<number> = 200,
    options: DebounceFilterOptions = {},
): UseDebounceFnReturn<T> {
    return createFilterWrapper(
        debounceFilter(ms, options),
        fn,
    )
}

export function debounceFilter(ms: MaybeRefOrGetter<number>, options: DebounceFilterOptions = {}) {
    let timer: TimerHandle
    let maxTimer: TimerHandle
    let lastRejector: AnyFn = noop

    const _clearTimeout = (timer: TimerHandle) => {
        clearTimeout(timer)
        lastRejector()
        lastRejector = noop
    }

    let lastInvoker: () => void

    const filter: EventFilter = (invoke) => {
        const duration = toValue(ms)
        const maxDuration = toValue(options.maxWait)

        if (timer)
            _clearTimeout(timer)

        if (duration <= 0 || (maxDuration !== undefined && maxDuration <= 0)) {
            if (maxTimer) {
                _clearTimeout(maxTimer)
                maxTimer = undefined
            }
            return Promise.resolve(invoke())
        }

        return new Promise((resolve, reject) => {
            lastRejector = options.rejectOnCancel ? reject : resolve
            lastInvoker = invoke
            // Create the maxTimer. Clears the regular timer on invoke
            if (maxDuration && !maxTimer) {
                maxTimer = setTimeout(() => {
                    if (timer)
                        _clearTimeout(timer)
                    maxTimer = undefined
                    resolve(lastInvoker())
                }, maxDuration)
            }

            // Create the regular timer. Clears the max timer on invoke
            timer = setTimeout(() => {
                if (maxTimer)
                    _clearTimeout(maxTimer)
                maxTimer = undefined
                resolve(invoke())
            }, duration)
        })
    }

    return filter
}

export function refDebounced<T>(value: Ref<T>, ms: MaybeRefOrGetter<number> = 200, options: DebounceFilterOptions = {}): RefDebouncedReturn<T> {
    const debounced = ref(toValue(value)) as Ref<T>

    const updater = useDebounceFn(() => {
        debounced.value = value.value
    }, ms, options)

    watch(value, () => updater())

    return shallowReadonly(debounced)
}
