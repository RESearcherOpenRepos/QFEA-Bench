# Dataset Scripts

Main workflow scripts:

- `pull_published_images.py`: Pull available cached `agent-base` images from
  DockerHub. Agent-specific images should normally be rebuilt locally from
  `benchmark-agent-base:<sample_id>`.
- `retag_published_images.py`: Retag pulled images to the local names used by
  the runners.
- `build_openhands_images.py`: Build OpenHands images from
  `benchmark-agent-base:<sample_id>`.
- `check_agent_images.py`: Check whether the Mini-SWE-Agent and OpenHands
  images exist and can start.
- `push_framework_images.py`: Push local framework images to a remote registry
  and record successfully pushed tags in a state JSON file so interrupted runs
  can resume.

Evaluator and local rebuild scripts:

- `build_base_images.py`: Build `benchmark-base:<sample_id>` from each
  sample's `Dockerfile.repo-base`.
- `build_evaluation_images.py`: Build `benchmark-evaluation:<sample_id>` from
  `benchmark-base:<sample_id>`.
- `build_agent_base_images.py`: Build leak-free
  `benchmark-agent-base:<sample_id>` images.
- `build_minisweagent_images.py`: Build mini-SWE-agent images from
  `benchmark-agent-base:<sample_id>`.
- `update_sample_index.py`: Regenerate
  `benchmark/dataset/samples/index.json`.

Optional adapter scripts:

- `build_traeagent_images.py`: Prepare Trae-agent images from
  `benchmark-agent-base:<sample_id>` when running legacy Trae-agent experiments.

One-off migration, backfill, and deep-check scripts live under `maintenance/`;
they are not part of the normal run workflow.

DockerHub release cleanup scripts also live under `maintenance/`. For example,
`delete_dockerhub_non_agent_base_tags.py` removes legacy adapter tags while
keeping the published `agent-base-*` tags.

Registry deletion utilities are maintainer-only operations, not reviewer setup steps.
