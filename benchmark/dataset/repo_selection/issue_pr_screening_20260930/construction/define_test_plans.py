import json,ast,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
rows=json.loads((R/'cohort.json').read_text())
def names(sid,path):
 t=ast.parse((R/'sources'/sid/path).read_text());out=[]
 def walk(t,ctx=''):
  for n in t.body:
   if isinstance(n,ast.ClassDef):walk(n,ctx+n.name+'::')
   elif isinstance(n,ast.FunctionDef) and n.name.startswith('test'):out.append(path+'::'+ctx+n.name)
 walk(t);return out
plans={
 'tequila_400_411':(['tests/test_recompilation_routines.py::test_compile_qubit_excitations'],[s for s in names('tequila_400_411','tests/test_recompilation_routines.py') if any(s.endswith(x) for x in ['test_compile_swap','test_compile_ry','test_compile_y','test_compile_ch'])]),
 'tequila_403_407':(names('tequila_403_407','tests/test_circuit_unitary.py'),[s for s in names('tequila_403_407','tests/test_circuits.py') if any(s.endswith(x) for x in ['test_qubit_map','test_conventions','test_basic_gates','test_variable_map','test_canonical_moments'])]),
 'tequila_406_409':(['tests/test_chemistry.py::test_wfn_fci'],['tests/test_chemistry.py::test_h2_hamiltonian_psi4','tests/test_chemistry.py::test_prepare_reference','tests/test_chemistry.py::test_orbital_transformation']),
 'qiskit_addon_sqd_148_230':(['test/test_fermion.py::TestFermion::test_diagonalize_fermionic_hamiltonian_max_dim'],['test/test_fermion.py::TestFermion::'+s for s in ['test_diagonalize_fermionic_hamiltonian_basic','test_diagonalize_fermionic_hamiltonian_reproducible_with_seed','test_bitstring_matrix_to_ci_strs','test_bitstring_matrix_to_ci_strs_large']]),
 'qiskit_addon_sqd_265_343':(['test/test_fermion.py::TestFermion::test_diagonalize_fermionic_hamiltonian_numpy_bitstrings'],['test/test_fermion.py::TestFermion::'+s for s in ['test_diagonalize_fermionic_hamiltonian_basic','test_diagonalize_fermionic_hamiltonian_max_dim','test_diagonalize_fermionic_hamiltonian_no_valid_bitstrings','test_bitstring_matrix_to_ci_strs','test_bitstring_matrix_to_ci_strs_large']]),
 'openqaoa_36_71':(names('openqaoa_36_71','tests/test_converters.py'),['tests/test_problems.py::TestProblem::'+s for s in ['test_qubo_terms_and_weight_same_size','test_qubo_cleaning_terms','test_qubo_cleaning_weights','test_maximumcut_terms_weights_constant','test_number_partitioning_terms_weights_constant']]),
 'openqaoa_112_85':(['tests/test_parameters.py::TestingQAOACircuitParams::'+s for s in ['test_QAOACircuitParams','test_QAOACircuitParams_mixer_coeffs_selector_gatemap','test_QAOACircuitParams_assign_coefficients']],['tests/test_parameters.py::TestingQAOAVariationalParameters::'+s for s in ['test_QAOAVariationalExtendedParams','test_QAOAVariationalStandardParams','test_QAOAVariationalAnnealingParams']]),
 'openqaoa_232_241':(['tests/test_operators.py::TestingOperators::test_hamiltonian_as_matrix'],[s for s in names('openqaoa_232_241','tests/test_operators.py') if '::test_hamiltonian_' in s and not s.endswith('as_matrix')]+['tests/test_operators.py::TestingOperators::test_pauli_matrix']),
 'squlearn_62_99':(names('squlearn_62_99','tests/qnn/test_base_qnn.py')+['tests/qnn/test_qnnr.py::TestQNNRegressor::test_set_params_and_fit','tests/qnn/test_qnnc.py::TestQNNClassifier::test_set_params_and_fit'],['tests/qnn/test_qnnr.py::TestQNNRegressor::test_predict_unfitted','tests/qnn/test_qnnc.py::TestQNNClassifier::test_predict_unfitted']),
 'squlearn_112_154':(names('squlearn_112_154','tests/qnn/test_loss.py'),['tests/qnn/test_qnnr.py::TestQNNRegressor::test_fit','tests/qnn/test_qnnr.py::TestQNNRegressor::test_predict']),
 'squlearn_274_279':(names('squlearn_274_279','tests/kernel/matrix/test_kernel_optimizer.py'),[s for s in names('squlearn_274_279','tests/kernel/ml/test_qkrr.py') if any(s.endswith(x) for x in ['test_predict','test_kernel_params_can_be_changed_after_initialization','test_encoding_circuit_params_can_be_changed_after_initialization'])]),
 'squlearn_275_339':(['tests/qnn/test_qnnr.py::TestQNNRegressor::test_serialization','tests/qnn/test_qnnc.py::TestQNNClassifier::test_serialization','tests/kernel/ml/test_qkrr.py::TestQKRR::test_serialization'],['tests/qnn/test_qnnr.py::TestQNNRegressor::test_fit_2out','tests/qnn/test_qnnr.py::TestQNNRegressor::test_partial_fit','tests/kernel/ml/test_qkrr.py::TestQKRR::test_predict']),
}
sid='squlearn_266_301';fp=[]
for p in (R/'sources'/sid/'tests/encoding_circuit/circuit_library').glob('test*.py'):
 fp += [s for s in names(sid,str(p.relative_to(R/'sources'/sid))) if s.endswith('test_minimal_fit')]
for p in (R/'sources'/sid/'tests/kernel/ml').glob('test*.py'):
 fp += [s for s in names(sid,str(p.relative_to(R/'sources'/sid))) if s.endswith('test_predict_without_num_features')]
plans[sid]=(fp,['tests/kernel/ml/test_qkrr.py::TestQKRR::test_predict','tests/qnn/test_qnnr.py::TestQNNRegressor::test_predict_unfitted'])
strong={'tequila_400_411','tequila_403_407','tequila_406_409','qiskit_addon_sqd_148_230','openqaoa_112_85','openqaoa_232_241'}
for r in rows:
 sid=r['sample_id']
 if sid not in plans:continue
 fp,pp=plans[sid]
 d={'sample_id':sid,'base_commit':r['base_commit'],'patch_commit':r['patch_commit'],'fail_pass':fp,'pass_pass':pp,'stage':'candidate_function_selectors_pending_collection','quantum_depth':'strong' if sid in strong else 'medium','quantum_depth_rationale':r['reason'],'annotation_evidence':'Issue/PR and test source only; no agent results inspected.'}
 (R/'jobs'/sid/'test_plan.json').write_text(json.dumps(d,indent=2)+'\n')
print('Prepared',len(plans),'candidate test plans; exact param nodeids pending collection')
