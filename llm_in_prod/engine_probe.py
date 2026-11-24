
import json, random, subprocess, sys, time

def gpu_used_gib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return round(int(out.split()[0]) / 1024, 2)

def random_prompt(seed, n):
    # random token ids: no two prompts share a prefix, so prefix caching cannot skip the work
    return {"prompt_token_ids": random.Random(seed).choices(range(1000, 20000), k=n)}

def main():
    from vllm import LLM, SamplingParams
    args = json.loads(sys.argv[1])
    n_requests = args.pop("n_requests", 256)       # probe setting, not an engine argument
    res = {}

    t0 = time.perf_counter()
    llm = LLM(seed=0, **args)
    res["startup (s)"] = round(time.perf_counter() - t0, 1)
    res["GPU used (GiB)"] = gpu_used_gib()
    try:
        res["max_num_batched_tokens"] = llm.llm_engine.vllm_config.scheduler_config.max_num_batched_tokens
    except Exception:
        pass

    def timed(prompts, params):
        t0 = time.perf_counter()
        outs = llm.generate(prompts, params, use_tqdm=False)
        return outs, time.perf_counter() - t0

    timed(["Hello"], SamplingParams(max_tokens=8))                                   # warm-up

    # 1. throughput: n_requests short prompts x 64 tokens (decode-heavy)
    prompts = [f"Write a short story about a robot named Unit-{i}." for i in range(n_requests)]
    outs, t = timed(prompts, SamplingParams(temperature=0, max_tokens=64, ignore_eos=True))
    res["throughput (tok/s)"] = round(sum(len(o.outputs[0].token_ids) for o in outs) / t)

    # 2. prefill: 32 prompts of 2,000 tokens x 1 token (prefill-heavy)
    _, t = timed([random_prompt(i, 2000) for i in range(32)], SamplingParams(max_tokens=1))
    res["prefill (tok/s)"] = round(32 * 2000 / t)

    # 3. one request: what a single user sees
    outs, t = timed(["Explain the KV cache."], SamplingParams(temperature=0, max_tokens=256, ignore_eos=True))
    res["single request (tok/s)"] = round(len(outs[0].outputs[0].token_ids) / t)

    # 4. a prompt longer than the default max_model_len
    try:
        timed([random_prompt(999, 5000)], SamplingParams(max_tokens=1))
        res["5k-token prompt"] = "ok"
    except Exception as e:
        res["5k-token prompt"] = "error: " + str(e)[:90]

    print("RESULT " + json.dumps(res), flush=True)

if __name__ == "__main__":      # vLLM starts the engine in a child process: the guard keeps it from re-running this file
    main()
