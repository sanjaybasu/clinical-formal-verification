export const meta = {
  name: 'civbench-blind-judge-suite_compute',
  description: 'Blinded LLM-as-judge over suite_compute; neutral ids and rule names; no label leakage',
  phases: [{ title: 'Judge', detail: 'one frontier-model agent per item' }],
}
const JUDGE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id','verdict','witness_assignment','witness_events','reasoning'],
  properties: {
    id: { type: 'string' }, verdict: { type: 'string', enum: ['holds','violated'] },
    witness_assignment: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['var','value'], properties: { var: { type: 'string' }, value: {} } } },
    witness_events: { type: 'array', items: { type: 'string' } },
    reasoning: { type: 'string' },
  },
}
const ids = ["item-032e616eee3e", "item-0d86264f924d", "item-13c97bd058c3", "item-187f8f98cae5", "item-18ff3c65935e", "item-19111354c7db", "item-1951f824e65a", "item-1b32f7cc5204", "item-1b3fd1e1ec47", "item-1c35d4615f8c", "item-1c6227731c27", "item-1ecafa1034d2", "item-38e1fb18614d", "item-395b7887487a", "item-3a065b4c941f", "item-46f3e8e4578d", "item-48cd5bb6fa52", "item-4992b3b0db64", "item-541fdda7e121", "item-5a0d08709898", "item-5b5b32c6064f", "item-5cb29a8181a7", "item-63d05a518aa5", "item-667fb0eb9d6f", "item-68ac93953c1d", "item-70e5ffe933b6", "item-76ae832618ec", "item-8c23e92079a0", "item-8ce49eadb40f", "item-910421fcc564", "item-91058dd77ea8", "item-96e9868bf7ba", "item-98d35870ee64", "item-9c5fb7546dc0", "item-9dbeb0f42487", "item-9fb423b401b1", "item-a08e8b572463", "item-a459e65fa5dd", "item-a69e15658b1f", "item-a91e98a89f7a", "item-abc21d28bc3d", "item-ad5ee6896ce1", "item-b0af23b550d3", "item-b0dfdea7ab76", "item-b64140a59b95", "item-bd2f35aed751", "item-bd642274643c", "item-c5015fb6cf9a", "item-c76633bfc599", "item-d8ed34960897", "item-dc62eb7b204b", "item-dcc5f4901900", "item-e1e6f404ad77", "item-e51ea011ff67", "item-e6a1f8dc4548", "item-f719c55f3e7d"]
const base = '/Users/sanjaybasu/clinical-formal-verification/experiments/runs_compute/_judge_prompts_blind'
const results = await parallel(ids.map((id) => () =>
  agent(
    `Read the file ${base}/${id}.txt . It specifies a clinical decision rule set (or state machine) and a safety property. ` +
    `Decide whether the property holds for the entire input space, or whether some input or execution violates it. Reason about rule interactions, priorities, defaults, and reachable states. Do not use web search or any tool other than reading that one file. ` +
    `Set id to "${id}". If violated, give a concrete counterexample in witness_assignment (decision systems: every input variable and value) or witness_events (state machines: the ordered event names). If it holds, leave both arrays empty. Many systems are correct; do not assume a violation exists.`,
    { label: `blindjudge:${id}`, phase: 'Judge', schema: JUDGE_SCHEMA }
  )
))
return results.filter(Boolean)
