with open('src/slokern/core/search/grid.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """            search_result = SearchResult(
                experiment_id=spec.experiment_id,
                baseline_candidate_id=configs[0].candidate_id,
                tested_candidates=tested_ids,
                candidate_summaries=candidate_summaries,
                ranking_objective=ranking_objective,
                selected_candidate_id=winner.candidate_id if winner else None,
                selection_rationale=rationale,
                stopping_reason=stopping_reason,
            )
            return GridSearchOutcome(search_result=search_result, run_results=run_results)"""

replacement = """            search_result = SearchResult(
                experiment_id=spec.experiment_id,
                baseline_candidate_id=configs[0].candidate_id,
                tested_candidates=tested_ids,
                candidate_summaries=candidate_summaries,
                ranking_objective=ranking_objective,
                selected_candidate_id=winner.candidate_id if winner else None,
                selection_rationale=rationale,
                stopping_reason=stopping_reason,
            )
            search_dir = self.artifacts_root / "experiments" / spec.experiment_id
            search_dir.mkdir(parents=True, exist_ok=True)
            (search_dir / "search_result.json").write_text(search_result.model_dump_json(indent=2), encoding="utf-8")
            return GridSearchOutcome(search_result=search_result, run_results=run_results)"""

if target in text:
    text = text.replace(target, replacement)
    with open('src/slokern/core/search/grid.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('Updated grid.py')
else:
    print('Target not found in grid.py')

with open('src/slokern/cli/commands/optimize.py', 'r', encoding='utf-8') as f:
    c_text = f.read()

c_target = """        outcome = controller.run(spec, ranking_objective=resolved_objective)
        search_res = outcome.search_result"""

c_replacement = """        outcome = controller.run(spec, ranking_objective=resolved_objective)
        search_res = outcome.search_result
        exp_dir = Path(output_dir or "artifacts") / "experiments" / spec.experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "search_result.json").write_text(search_res.model_dump_json(indent=2), encoding="utf-8")"""

if c_target in c_text:
    c_text = c_text.replace(c_target, c_replacement)
    with open('src/slokern/cli/commands/optimize.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(c_text)
    print('Updated optimize.py')
else:
    print('Target not found in optimize.py')

