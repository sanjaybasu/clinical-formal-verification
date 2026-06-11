export const meta = {
  name: 'civbench-blind-judge-suite_hard',
  description: 'Blinded LLM-as-judge over suite_hard; neutral ids and rule names; no label leakage',
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
const ids = ["item-01a073e50abd", "item-0b357cca9c3b", "item-0ba5b7ad26fd", "item-0c37b4d33bd1", "item-0d83c4829f42", "item-0d8926b469b9", "item-0e33dbfff287", "item-1478b57975c8", "item-161cf8979d55", "item-1aebafd354c5", "item-1d602e8a492f", "item-221c3815ce6c", "item-22a5406bd879", "item-26775c518c27", "item-29bb6213b4aa", "item-3d2371229a5a", "item-3f922e83c1c9", "item-42ff4a1cb3fb", "item-480769a96735", "item-4ba4f6f8944f", "item-4c3e7c10f323", "item-4dab6ad7ed70", "item-50fb72f92297", "item-55b972e9faaf", "item-5982f78cacf7", "item-5e0eb083be28", "item-604c9d5f3b91", "item-618fc60777d7", "item-6406e5d3fd67", "item-6cbfa016f160", "item-7904e961500a", "item-7b745f90925e", "item-7ffe021d389a", "item-a3c815521125", "item-a7ba7349216a", "item-b223ee496650", "item-b2cbeae28bc4", "item-b2d294e4982c", "item-bd7d53b16459", "item-c0407c444368", "item-c1375a3f331c", "item-c3e1635780cd", "item-c6ec32187638", "item-c93abf0ba8a3", "item-cda4843b60fc", "item-d051924f78d7", "item-d264765f2382", "item-d410f7a7d1f9", "item-dd53838f893c", "item-e04f88b2185b", "item-e2fc0cce2e56", "item-e4f691af2043", "item-e57d07fc9c79", "item-eb7ef60e6897", "item-f054ec8d7bc2", "item-f1773d634f7b", "item-f6c86a46bd52", "item-f790f3922622", "item-f8c7f50503b6", "item-fa22c55c2422"]
const base = '/Users/sanjaybasu/clinical-formal-verification/experiments/runs_hard/_judge_prompts_blind'
const results = await parallel(ids.map((id) => () =>
  agent(
    `Read the file ${base}/${id}.txt . It specifies a clinical decision rule set (or state machine) and a safety property. ` +
    `Decide whether the property holds for the entire input space, or whether some input or execution violates it. Reason about rule interactions, priorities, defaults, and reachable states. Do not use web search or any tool other than reading that one file. ` +
    `Set id to "${id}". If violated, give a concrete counterexample in witness_assignment (decision systems: every input variable and value) or witness_events (state machines: the ordered event names). If it holds, leave both arrays empty. Many systems are correct; do not assume a violation exists.`,
    { label: `blindjudge:${id}`, phase: 'Judge', schema: JUDGE_SCHEMA }
  )
))
return results.filter(Boolean)
