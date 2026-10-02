# RQ3: test constraints and task resolution

The active cohort contains **117 tasks and 1,617 selected tests** (623 F2P and
994 P2P). The annotation archive retains 119 historical task files; the active
index excludes IDs 117 and 119. Fifteen casewise replay files cover the three
agents and five models.

## Inputs and outputs

- [sample_constraint_annotations/](results/sample_constraint_annotations/) records one primary label per selected test, assertion locations, rationale, and source provenance.
- [constraint_subcategory_mapping.json](results/constraint_subcategory_mapping.json) maps raw labels to the seven paper categories.
- [casewise_replays/](results/casewise_replays/) contains structured selected-selector outcomes, including resource corrections.
- [RQ1 merged evaluations](../rq1/results/current/evaluations/) provides the active lightweight outcomes used across RQs.
- [summary/](results/summary/) contains category/subcategory pass rates, inventories, task-resolution comparisons, bootstrap/stratified checks, and replay quality.
- [additions_20261002/](results/additions_20261002/) preserves explicit extension decisions and original 106-task casewise snapshots.

Rebuild summaries from the repository root without model calls or Docker:

```bash
python3 rq/rq3/scripts/summarize_casewise_by_agent.py
python3 rq/rq3/scripts/summarize_casewise_by_subcategory.py
python3 rq/rq3/scripts/summarize_sample_resolution_by_constraint.py
python3 rq/rq3/scripts/audit_casewise_replays.py
```

`plot_constraint_overview.py` writes figures under `results/figures/` and requires
NumPy/Matplotlib. `extend_casewise_additions.py` rebuilds the active extensions from
saved outcomes and preserves the original 106 rows; it does not generate patches.
Optional `summarize_structured_constraint_passes.py` and
`summarize_casewise_by_subtype.py` write disposable per-setting CSVs under
`results/intermediate/`. `replay_saved_agent_results.py` exports these only when
`--export-intermediate` is requested.

## Paper taxonomy

| Internal semantic group | Paper name | Assertion-level distinction |
| --- | --- | --- |
| algebraic_numeric_computation | Mathematical Operations | General scalar, symbolic, matrix, tensor, conjugation, transpose, or numerical operations without quantum-specific expected relations |
| model_data_transformation | Data Processing | Structure/information preservation during model conversion, encoding, batching, topology, geometry, caching, or input transfer |
| learning_optimization_outcome | Algorithmic Solving | Loss objectives, gradients, prediction/training quality, convergence, objective values, solver failure, or decoded solutions |
| operator_algebra_and_mapping | Operator Semantics | Commutation, fermionic signs, normal ordering, Hermiticity, particle conservation, Pauli mappings, symmetry reduction, or representation equivalence |
| state_circuit_and_measurement | Circuit Semantics | Prepared states, circuit decomposition, expectation values, sampling fidelity, quantum-kernel overlaps, or QNN/QNode gradients |
| hamiltonian_chemistry_quantum_optimization | Application Semantics | Domain models/results such as electronic integrals, molecular/lattice Hamiltonians, excitations, density matrices, energies, QRAC, and quantum optimization |
| interface | Interface | Callable availability, inputs, exceptions, and exposed output representation |

Classify the asserted property, not its name: ordinary coefficient scaling differs
from fermionic anticommutation; QUBO expression conversion differs from a solved
objective; Hamiltonian representation equivalence differs from constructing the
correct molecular Hamiltonian; Hartree–Fock occupation bits differ from molecular
energy; matrix assembly differs from a quantum-kernel overlap assertion.

Each test keeps one primary label, while a task can span categories. Per-category
task counts overlap and cannot be summed into a distinct-task denominator. These
are operational categories for this dataset, not a universal testing standard.
Subcategory pass rates describe different test sets and are not failure-cause
percentages; limited category coverage remains a limitation.

## Extension evidence

The original extension reviewed 166 selectors for IDs 107–119 at their reference
commits, including helpers and assertion locations. Decisions and their writer are
stored under `results/additions_20261002/`. The added source review was assisted by
Codex; it is not three new independent human votes. Author-confirmed agreement is
recorded separately in [the agreement record](../rq4/results/annotation_agreement_confirmation.json).

Boundary decisions include nonexecuted conditional assertions in ID107, the last
effective definition of duplicate test names in ID109, interface-focused dimension
checks in IDs110/111, ordinary prediction/serialization checks in IDs117/119, and
fixed circuit/observable numerical references in ID114. Historical 119-task counts
are preserved as evidence; release summaries filter the active index.

## Annotation protocol

### Unit and order

The primary ID belongs to a benchmark sample, not a test. `benchmark/dataset/samples/index.json` is the authority for the 117 active IDs (stable IDs 1–119 excluding 117 and 119). Historical annotations for excluded tasks remain archived and must be filtered through that index. Within each sample, review every listed F2P and P2P selector in `sample.json` at the sample's exact patch commit. A listed selector is one test record; parameterized selectors may produce multiple runtime pytest items.

Each reviewed sample has one JSON file in `sample_constraint_annotations/`. Its `tests` array preserves F2P list order followed by P2P list order. `test_number` is local to that sample and is not a dataset-wide ID. Each test receives exactly one primary `label`. Its `assertions` array retains the relevant line numbers and expected behaviors, including aspects that do not become separate labels. When assertions cover several contracts, choose the contract that the test most directly checks and record the boundary decision in the rationale.

Each newly reviewed test also records a per-test `rationale` explaining why that single label fits the selected assertion. Code may validate selector coverage, source locations, and aggregate counts; it must not assign semantic labels from names, keywords, or rules in place of reading the test.

For a selected test that delegates its check to a helper, an assertion entry may point to the assertion in that helper and include `via_helper` with the selected test's call-site line and `helper_selector` with the helper's source selector. The source file remains the one named by the test selector.

If a selected test method is inherited, retain the selected runtime `selector` and add `source_file` and `source_selector` to identify the base method containing its assertion. Read the selected class setup as well as the inherited method: the same assertion can check a direct driver result or a save/load round trip depending on that setup.

### Top-level labels

- `general_semantics`: The assertion checks ordinary program behavior without requiring quantum meaning.
- `quantum_semantics`: The assertion checks a quantum or quantum-chemistry concept, convention, or invariant.
- `interface`: The assertion checks a callable's availability, accepted inputs, exception contract, or exposed return representation.

Read the task for context, then assign the primary label from the asserted behavior, not from the task description, test split, or an agent failure mode. This annotation does not assess whether the tests cover or match the task. Setup operations and implicit expectations that a call exists do not create additional labels. `assertTrue` and `assertFalse` establish truthiness rather than an exact return type. Direct checks of an exposed result container may be labeled as interface constraints even when their setup has quantum meaning. Count each test once in category statistics and report F2P and P2P separately. A failed test in a category shows which contract it checks; the label alone does not establish the failure's root cause.

When pytest fails during collection, retain the observed testcase outcome as `not_collected` with `phase=collection` for selectors in the affected file. The F2P/P2P suite fails because pytest exited unsuccessfully; this does not imply that each selected testcase executed and failed an assertion. Root-cause attribution to the submitted patch or evaluation environment is a separate sample-level analysis. The evaluator may report one collection error per file rather than one per selected test. Report the all-selected pass rate as primary and separately identify collection-phase failures. The final raw subtype vocabulary is consolidated into six semantic subcategories plus Interface in `constraint_subcategory_mapping.json`; the paper-facing names and definitions are in the Paper taxonomy section above.

The original Agent–LLM evaluation JSON did not record exact testcase outcomes. The final results in `casewise_replays/` replay the saved patches and provide a structured `test_cases` record for every selected selector, including `passed`, `failed`, `skipped`, `not_collected`, and `not_run`; F2P/P2P suite status is calculated from these records. An uncollected selector has no observed pass/fail result even when the submitted patch caused a collection failure. Final paper statistics are derived from these structured records, rather than inferred from pytest text logs.

### Raw subtype examples

- `general_semantics/noncommutative_series`: Evaluating a general truncated noncommutative series on ordinary matrix-like inputs.
- `general_semantics/algebraic_identity`: Checking a universal algebraic identity that does not depend on quantum operator rules.
- `general_semantics/symbolic_operator_arithmetic`: Generic coefficient scaling and term aggregation in a symbolic operator container, without a quantum-specific expected relation.
- `general_semantics/grid_topology`: Counting sites and adjacency relations in a grid independently of quantum operator values.
- `general_semantics/binary_linear_algebra`: Computing reduced row echelon forms and nullspaces over GF(2).
- `general_semantics/effective_dimension_calculation`: Matching a statistical effective-dimension calculation to numeric references.
- `general_semantics/kernel_matrix_construction`: Constructing numeric square, rectangular, or batched kernel matrices with expected entries.
- `general_semantics/lossless_chunk_partitioning`: Enforcing chunk bounds and restoring all input entries after recombination.
- `general_semantics/model_training_performance`: Meeting an ordinary classifier or regressor score threshold after fitting.
- `general_semantics/numeric_tolerance_filtering`: Retaining or dropping numeric terms at specified coefficient thresholds.
- `general_semantics/portfolio_metrics`: Computing portfolio return and variance from vectors and covariance matrices.
- `general_semantics/portfolio_selection_decoding`: Decoding asset-selection variables to selected indices.
- `general_semantics/quadratic_program_construction`: Constructing the prescribed objective and constraints of a portfolio program.
- `general_semantics/warm_start_optimization_state`: Reusing previous fitted weights as the next optimization start.
- `quantum_semantics/operator_normal_ordering`: Whether creation and annihilation operators in a bosonic or fermionic term satisfy that operator's normal-order rule, including empty and multi-term cases.
- `quantum_semantics/boson_number_conservation`: Whether bosonic ladder operators preserve total boson number, including an empty operator and terms whose creation/annihilation operators appear out of order.
- `quantum_semantics/active_space_projection`: Removing occupied or unoccupied frozen orbitals from a fermionic operator, including the resulting coefficients and orbital indices.
- `quantum_semantics/molecular_term_classification`: Recognizing fermionic terms with the allowed ladder count and particle-number and spin conservation.
- `quantum_semantics/hamiltonian_representation_equivalence`: Preserving the same Hamiltonian under conversion among fermionic, diagonal-Coulomb, quadratic, sparse-matrix, and Jordan–Wigner representations.
- `quantum_semantics/hamiltonian_domain_validity`: Rejecting operators that do not satisfy a target Hamiltonian form's mathematical conditions, such as quadratic degree or Hermiticity.
- `quantum_semantics/fermionic_tensor_mapping`: Mapping fermionic one- and two-body terms to the correct tensor indices and coefficients.
- `quantum_semantics/majorana_operator_convention`: Constructing Majorana operators with the specified creation/annihilation signs and normalization.
- `quantum_semantics/spin_operator_algebra`: Constructing fermionic spin generators and composite spin operators with the expected algebra.
- `quantum_semantics/ground_state_energy`: Matching the ground-state energy of a Hamiltonian against an independent energy calculation.
- `quantum_semantics/operator_locality`: Bounding how many qubits a transformed operator term acts on.
- `quantum_semantics/fermion_qubit_mapping`: Mapping fermionic ladder and identity operators to the correct qubit Pauli operators and coefficients.
- `quantum_semantics/spectral_equivalence`: Preserving an observable's eigenspectrum across fermion-to-qubit representations.
- `quantum_semantics/fermionic_commutation`: Checking commutators of fermionic ladder-operator expressions, including cancellations and resulting hopping terms.
- `quantum_semantics/pauli_commutation`: Checking the Pauli operator commutation relations.
- `quantum_semantics/majorana_operator_algebra`: Canonicalizing Majorana products and checking their commutation and multiplication signs.
- `quantum_semantics/hubbard_hamiltonian_construction`: Mapping lattice tunneling, interaction, and potential parameters to the expected fermionic Hamiltonian terms and multiplicities.
- `quantum_semantics/fermionic_basis_rotation`: Preserving one- and two-body fermionic coefficient tensors under the specified orbital-basis transformation.
- `quantum_semantics/interaction_tensor_symmetry`: Enumerating one- and two-body interaction tensor entries once per four- or eight-point symmetry class.
- `quantum_semantics/circuit_decomposition`: Matching the prescribed decomposed circuit or its operation count.
- `quantum_semantics/clifford_operator_construction`: Constructing the expected Clifford operator from Pauli symmetries.
- `quantum_semantics/diagonal_coulomb_projection`: Retaining the expected one- and two-body coefficients when projecting to diagonal-Coulomb form.
- `quantum_semantics/fermion_qubit_parity_mapping`: Mapping fermionic terms to the Pauli images prescribed by the parity encoding.
- `quantum_semantics/fermionic_matrix_representation`: Producing the matrix action of fermionic words or weighted sentences.
- `quantum_semantics/fermionic_operator_conversion`: Preserving ladder terms and coefficients across fermionic operator representations.
- `quantum_semantics/fermionic_zero_operator`: Recognizing a fermionic expression that cancels to the zero qubit operator.
- `quantum_semantics/hamiltonian_tapering`: Preserving the specified Hamiltonian coefficients and Pauli terms after symmetry tapering.
- `quantum_semantics/hartree_fock_tapering`: Mapping a Hartree-Fock occupation state to its tapered state.
- `quantum_semantics/majorana_fermion_mapping`: Preserving Majorana and fermionic ladder-operator expansions in both directions.
- `quantum_semantics/pauli_symmetry_construction`: Producing the Pauli operators prescribed by symmetry generators.
- `quantum_semantics/probability_state_preparation`: Preparing statevector amplitudes for a discretized probability distribution.
- `quantum_semantics/qnn_representation_equivalence`: Agreeing on a quantum-model result across circuit and operator-flow QNN representations.
- `quantum_semantics/qnode_gradient_consistency`: Matching trainable QNode gradients through a neural-network wrapper.
- `quantum_semantics/quantum_kernel_evaluation`: Matching quantum feature-map overlap matrices to numerical references.
- `quantum_semantics/qubit_operator_conversion`: Preserving Pauli words and coefficients across library operator representations.
- `quantum_semantics/state_preparation_correctness`: Preparing the prescribed quantum state after parameter binding or circuit composition.
- `quantum_semantics/tapering_expectation_preservation`: Preserving observable expectation values under state and operator tapering.
- `interface/return_representation`: Requiring a particular exposed container or encoding for a result, such as an empty `terms` mapping for a zero operator.
- `interface/input_validation`: Rejecting unsupported input types or invalid argument ranges with the specified exception behavior.
- `interface/coefficient_type_acceptance`: Accepting a specified scalar or symbolic coefficient type in a public constructor and exposing it for the constructed term.
- `interface/string_representation`: Requiring the exact public string form of zero, identity, and one- or multi-term operators.
- `interface/lattice_edge_type_contract`: Exposing supported lattice edge names and rejecting unknown edge-type names.
- `interface/constructor_defaults`: Requiring specified default values for public constructor options or parameter collections.
- `interface/tensor_key_compatibility`: Rejecting arithmetic between coefficient tensors whose action-pattern key sets are incompatible.
- `interface/broadcasted_layer_shape`: Keeping all leading input dimensions in a wrapped layer's output and preserving gradient availability.
- `interface/callable_optimizer_support`: Accepting a callable optimizer in public fitting APIs and exposing fitted results.
- `interface/callback_invocation`: Invoking an optimization callback the prescribed number of times.
- `interface/circuit_parameter_contract`: Exposing the expected circuit parameter count or error before binding.
- `interface/class_count_contract`: Reporting the number of classes after label processing.
- `interface/class_label_roundtrip`: Returning predictions in the original integer or categorical label representation.
- `interface/coefficient_tolerance_contract`: Applying a public tolerance option to retained terms or imaginary coefficient parts.
- `interface/coefficient_type_tolerance`: Exposing the expected numeric coefficient type after tolerance handling.
- `interface/gradient_shape`: Returning gradients with the documented dimensions or absence.
- `interface/hybrid_module_training_contract`: Exposing trainable quantum and classical parameters with gradients through a hybrid module.
- `interface/input_format_equivalence`: Accepting alternate public input representations with equivalent results.
- `interface/kernel_callback_invocation`: Calling a supplied kernel function in the specified order and skipping normalized diagonals.
- `interface/missing_key_lookup`: Returning the documented value for a missing container key.
- `interface/model_serialization_roundtrip`: Preserving fitted predictions across save/load and checking loaded class type.
- `interface/optional_dependency_error`: Reporting a clear import error when an optional library is unavailable.
- `interface/output_shape`: Returning the documented tensor or matrix dimensions.
- `interface/property_mutability`: Exposing an assigned configuration value through its public property.
- `interface/serialization_roundtrip`: Preserving a public data object through pickle serialization.
- `interface/sparse_input_compatibility`: Accepting sparse features or labels in fitting and scoring APIs.
- `interface/training_callback_payload`: Passing float objectives and correctly sized numeric weights to training callbacks.
- `interface/user_parameter_binding`: Exposing, validating, and updating user-specified QNN or kernel parameters.
- `interface/wire_mapping_contract`: Honoring or validating caller-supplied wire and orbital labels.
- `interface/zero_operator_representation`: Exposing the documented empty or zero-valued container form.

The raw subtype labels are mapped to the paper categories in `constraint_subcategory_mapping.json`. Fermionic signs and orbital renumbering are recorded in the evidence for sample 2 but are not separately counted there. Exception syntax alone does not decide a test's label: sample 3's broad rejection test is input validation, while its focused nonquadratic and non-Hermitian tests concern mathematical admissibility. F2P and P2P are retained as separate test roles; neither role determines a semantic label.
