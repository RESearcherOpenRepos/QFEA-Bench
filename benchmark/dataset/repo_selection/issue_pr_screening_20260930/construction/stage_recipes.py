"""Stage unvalidated Docker recipes; never add untested samples to the dataset."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATASET=ROOT.parents[2]
rows=json.loads((ROOT/'cohort.json').read_text())
for r in rows:
 if r['current_issue_state']!='closed':continue
 sid=r['sample_id'];job=ROOT/'jobs'/sid;job.mkdir(parents=True,exist_ok=True)
 # Start with PR metadata; dependency compatibility must be resolved and frozen during real builds.
 deps=['pytest']
 constraints=[]
 if sid.startswith('tequila'):
  deps+=['qulacs']
  if sid=='tequila_403_407':deps+=['quimb']
  if sid=='tequila_406_409':deps+=['pyscf']
 if sid.startswith('squlearn'):
  if sid in ['squlearn_112_154','squlearn_266_301','squlearn_275_339']:
   constraints=['qiskit==1.1.2','qiskit-ibm-runtime==0.27.1','autoray==0.7.2']
  elif sid=='squlearn_274_279':
   constraints=['qiskit==1.0.2','qiskit-aer==0.14.2','qiskit-ibm-runtime==0.23.0','qiskit-machine-learning==0.7.2','qiskit-algorithms==0.3.0','pennylane==0.36.0','autoray==0.6.11','bayesian-optimization<2']
  elif sid=='squlearn_62_99':
   constraints=['qiskit==0.44.0','qiskit-aer==0.12.2','qiskit-machine-learning==0.6.1','qiskit-ibm-runtime==0.11.3','numpy<2','scikit-learn<1.4']
 if sid.startswith('openqaoa'):
  constraints=['numpy<2','networkx<3','pyquil<4','qiskit<1','Cython<3']
 (job/'constraints.txt').write_text('\n'.join(constraints)+'\n')
 docker=f'''# Initial recipe only: NOT built or runtime validated.
# syntax=docker/dockerfile:1
FROM python:3.10-slim-trixie
ENV DEBIAN_FRONTEND=noninteractive OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends git gcc g++ gfortran make libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/repo
RUN git init && git remote add origin https://github.com/{r['repository']}.git && git fetch --depth=2 origin {r['patch_commit']} && git checkout --detach {r['patch_commit']} && git cat-file -e {r['base_commit']}^{{commit}}
COPY constraints.txt /opt/constraints.txt
RUN --mount=type=cache,id=quanbench-pip,target=/root/.cache/pip python -m pip install 'pip<25' 'setuptools<81' wheel && python -m pip install -c /opt/constraints.txt -e . {' '.join(deps)} && python -m pip freeze > /opt/build-freeze.txt
'''
 (job/'Dockerfile.repo-base').write_text(docker)
 (job/'Dockerfile').write_text(f'''# Initial recipe only; exact selectors must be supplied after pytest collection.
FROM benchmark-base:{sid}
ENV SAMPLE_ID={sid} REPOSITORY={r['repository']} REPOSITORY_URL=https://github.com/{r['repository']}.git
ENV BASE_COMMIT={r['base_commit']} PATCHED_COMMIT={r['patch_commit']} GIT_NO_LAZY_FETCH=1
ENV ISSUE_URL={r['issue_url']} PR_URL={r['pr_url']}
COPY run.sh /benchmark/run.sh
ENTRYPOINT ["bash", "/benchmark/run.sh"]
''')
 shutil.copyfile(DATASET/'templates/run.sh.template',job/'run.sh')
 plan={**r,'status':'blocked_docker_storage_unavailable','recipe_status':'draft_unbuilt','fail_pass_hint':r['target_tests'],'selected_fail_pass':None,'selected_pass_pass':None,'stability_runs':0,'official_validation_runs':0,'dependency_lock_complete':False,'task_fields_complete':False,'golden_patch_scope_complete':False,'constraints_rationale':'Initial compatibility constraints based on cached PR-era project/CI metadata; additional bounds are provisional and require actual build/import validation. No sample is accepted on this basis.'}
 (job/'construction_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print('Staged',sum(r['current_issue_state']=='closed' for r in rows),'unbuilt recipes')
