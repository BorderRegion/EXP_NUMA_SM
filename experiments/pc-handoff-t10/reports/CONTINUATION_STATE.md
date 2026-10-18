# 历史中途交接记录——已被最终报告取代

以下是执行期间留下的检查点，并非当前进度。GPU 队列现已完成，当前状态见 ../STATUS.md 和 ../T10_PC_HANDOFF_LLM_REPORT.md。保留本文件只为解释工程过程。

# Live continuation checkpoint — 2026-10-16 13:25 UTC

Do not stop at this checkpoint. User asked “扎实完成” for T10_PC_HANDOFF_LLM_20261016.zip. Execute the permitted complete local-source/weak-result branch; final report + verified compact ZIP required. Offline, no download/install/SSH/other GPU, one GPU worker under shared flock,24 worker-hour cap, protections stay100W. No subagents/new task/goal/automation. Chinese meaningful updates roughly every minute. Full experiment design is in input/.../CODEX_MASTER_TASK.md and docs; docs03 section7 explicitly allows dependency contraction as F1, so actual activation epilogue fusion is an untested alternative, NOT an unmet mandatory F1 requirement.

## Live execution
- root: /home/ubuntu/文档/ChatGPT/numa_gpu/pc-handoff-t10
- Python: /home/ubuntu/projects/leetgpu-lab/.venv/bin/python3
- run: runs/20261016T112633Z (CURRENT_RUN.txt)
- GPU finite serial queue now DETACHED from terminal; do NOT restart a duplicate.
- Supervisor PID2787856 (recover_parent.py), queue child2787863. Read run/DETACHED_QUEUE_PID.txt and detached_queue.log; inspect current raw/*/manifest.json and stdout/stderr. Queue currently entering E3 (at13:23:44 UTC). At13:25 one E3 block partly complete.
- Old exec sessions72071,70300 have ended. 70300 unexpectedly returned143, killing parent and monitor while E2_bridge_1 continued. Adopted child without restarting GPU computation. E2_bridge_1 has54 PASS phases +complete marker after engine close, returncode unavailable, telemetry gap explicitly recorded; conservative worker debit includes recovery observation delay. Source/metadata preserved. New queue detached; future worker children inherit lock fd, wrapper handlesSIGTERM by settling/stopping child. See engineering notes.
- All E1, all four E2 matrices, all four bridges complete. Matrix3072 cells. Actual E2_bridge_0 failed before any phase due host ostringstream metadata; successful replacement is E2_bridge_0_retry01, mapping in freeze/worker_retry_map.json. common.worker_dir/key resolves it. Never overwrite failed raw.
- Branch frozen reduced: E3 fixed12test×6blocks CORE/M/P/G+LIB anchors;M=G alias. No test tuning.
- Next queue: E3 six blocks; E4 native dev+6testblocks; E5 GEMM6blocks, attention6blocks, ablation6, workspace4, lifetime3; E6eightprofiles. Final run/GPU_EXECUTION_COMPLETE.json only written at very end. Do not call launch/completion of a few blocks “finished”.

## Scientific frozen findings
- pc_rule partition1,pi0, selected on first2PC processes. M==G exactly. No new pairing information vs simple same-group. Partition selection vsdefault partition not independently tested; don't claim it.
- isolated confirmation batch M/reverse gains: block2 -0.2541%, block3 +0.6126%; single-request +0.0445%,+0.6512%. Weak/inconsistent, no stable general locality evidence. W/case details in derived.
- Completed4bridgeprocesses: M/LIB GPUgain -4.8328%,95%CI[-14.290,+3.842]; batchgain -13.8933%,CI[-20.167,-10.377]. M/P GPUgain-.9339%,CI[-2.377,+.489]; batch+.3817%,CI[-.283,1.082]. Heterogeneous shape effects, do not rename reversewinner.
- E1 selected6representatives R proxy1%-8%; full16development includesG031~17%, retain it. Some forcedsplit bins, productionM<=8/M>128S1;midMS2. AllwideNtest inheritsnarrowNrule, no test tuning.
- Main build currently build/20261016T130724Z. Same qualified math cubins as123041; onlyhostDAG metadata repaired to avoid ctypes/libstdc++localeostreamSIGSEGV. Actual CUDA Graph node names/grid/edges validated after repair in qualify_dag_fixed. NativecuBLASactualfunctioncaptured, CORE2nodes,controlled4nodes.
- Frozen isolated matrix usesbuild115221. All six C++/CUDA/adapters files in freeze/implementation match that build source hashes exactly. Parent wrapper manifests samplednewerBUILD before childPC_BUILD override; authoritative childstdout, matrix_build.json and matrix_manifest_clarification.json explicitly distinguish.

## Implemented and qualified since previous checkpoint
- Ragged attention truly per-batch lengths choices[(request+b)%3], timedQ/KVappend/length/mask; seedednonzeroresidual, phaseKVreset. qualify_ragged4phases plus4fullFP64mask/large-logit checks PASS (fullymaskedrowzero). Nativeattentiononly; candidate ADAPTER_MISSING. No new splitKVmath.
- Attention CUDA Graph debugDOT dumped outside timing; graph_build_ms excludesDOTwrite. E6eighthprofile upgraded to completeB4GQAraggedchain.
- FFN same-body bitwise checks now check firstGEMM and downstreamfinaloutput.
- Before ANY E3/E5 data, repaired execution-order balance afterM/Galiascollapse. E3 threeactualCORE/M/Pall6permutations across6blocks, G aliasM. FFN LIB/CORE/M similarlybalanced. F0/F1 andplanar/slab alternateorder. Workspace4conditions full4Williamsrows. Freeze formal_execution_order.json documents rationale andpretesttimestamp. No method/mapping/recipe changes.
- CPU original31 tests and new3geometrytests PASS, logs inreports. No furthermathchanges justifyretestingGPUqualification.
- Current source_audit.py must rerun at end because newhostbuild and scriptschanged; source_audit confirms HMMA inall4producerrecipes, noSMID/CLOCKanywhereDIAG0, exactmathcubinidentity toqualifiedproduction.

## Final analysis/report tooling prepared, NOT yet final
- src/analyze.py CPUonly readsrunrawmanifests,allphases/NA,aliases; fullblockbootstrap50k(seed20261016),equalcase logratios,97.5%E3M/LIB,M/G,95%exploratory; allpairvalues,caseintervals,PCraw/log/additive residual, case/Wconfirmation, descriptive residualstability, E1baselinecards,telemetry(includingresumeCSV),initamortization,actualDAG,correctnessinventory. Includes incompletephases inexport but onlycompletedworkers ininference; rerun afterqueuecomplete.
- src/figures.py staticPNG/PDF. Baseline andPCfigs inspected; PCtoprowxlabeloverlapwasfixed byonlybottomxlabel,height7. Need rerun allandVISUALLYinspect finalforest/controlfigs. Currentlysomepartialfigs exist; overwrite derivedfigs atfinal. Forest skipsmissingCIs. Consider symlog forSCRATCHcontrolchart if otherssqueezed.
- src/final_audit.py onlyafterGPUcomplete; checks exactphasecounts (E1 352/block;matrix768;bridge54;E3 60;native24;FFN30;attnchain24;ablation24;workspace12), actualE3orderbalanced,12×6paircoverage,4nodeDAG,budget,originalfourpowerfilehashes100Wservices; writesFINAL_POWER_READBACK andFINAL_COMPLETENESS_AUDIT.
- src/report.py onlyafterfinal_audit andanalyze; rendersrequiredROOT/T10_PC_HANDOFF_LLM_REPORT.md, reports/CONTRIBUTION_CARD.md andPLAIN_LANGUAGE_RESULTS.md. LongChinesecompleteRQreportwithallknownlimits/NA/figs anddynamicstats. MUST review actualgeneratedreportforfactual/formattingbugs, especiallyclassification ifmainresultpositive, completedcounts, caveats. “No methodincrementvsG”alwaysvalid, doesNOTautomaticallymeanalllayout/fusionengineeringgainsabsent. IncludesPCcase/Wconfirmationtable, parentrecoverygap, orderamendment, F1allowedbranch.
- src/recompute.py CPUonly regeneratesfromexportedrunandbytecomparescomparisons/casecomparisons/PCconfirmation/pairedvalues/PCcontrasts/dev/init; fullFP64 check of savedactualGPUoutput65×196×512. NoGPUrerunclaimed.
- src/package.py afterfinalreport/audit/visualQA: makesreview_staging/newtimestamp, allsource/freeze/input/derived/reports, allphase/correctness/etc +telemetry/DOT/failurelogs, first3samplelinesfromrepresentativeworkers, qualifiedmatrix+latestbinaries/SASS/allbuildrecords,optional2smallprofiles. RunsCPUrecomputeinstaging, createsFILE_MANIFEST, writesDownload/T10_PC_HANDOFF_LLM_RESULTS_20261016_SMALL.zip (neveroverwritesprior), reextractsfreshandchecksallhashes/recompute, alsofullrawZIP, writesreports/DELIVERY.json. Checksize,zipcontentsandfinalproof. WARNING: reports/copiedsource andfreeze finalsourcehashes shouldbe finalized beforepackage; FRESH_ARCHIVE proof outsideZIP but stagingproofinside. No vendor/modelduplication.
- README_REPRODUCE.md explainsCPUcommandandmachine-specificGPUdependencies/limitations.
- Gitbranchcodex/t10-pc-handoff; allnewrootuntracked, .gitignoreexcludesbuild/runs/review_staging/zip/pycache. Stageonlynewsource/docs/freeze/derived/reports etc afterfinal; avoidhugefiles ifunnecessary. Commitno push. No oldexperimentsmodified.

## Pending priority
1 Monitor detachedqueue completion/failures; fixordinaryissueswithoutquestion, preserveattempts andresumeappropriateids. NoGPUconcurrency.
2 Onfinish run analyze, source_audit, final_audit, figures, report. Review numericclaims/figurelayout; allNAhonest. Data integrityassertions aren'tspeedupgates.
3 Fullcompleteartifactpack+fresh-extractionCPUrecompute, ensurepowerandnoexperimentalGPUworkerleft.
4 OptionalopenreportinCodex. FinalChineseconciseoutcome, realfigures/limits, reportandSMALLziplinks (fullrawoptional), no claimunimplementedattentioncandidate. Do notendearly.

##13:41UTC-ish update (local21:41)
E3 allsixblocks COMPLETED, each60phases/orderverified. M/LIB GPUgain-26.423%,97.5%CI[-28.653,-24.452]; CORE/LIB-22.777%,95%CI[-24.475,-21.093];M/CORE-2.969%,CI[-5.148,-1.061];M/P-2.275%,CI[-5.336,+.665];M/Gexact0. BatchM/LIB-39.005%;M/P-.991%CI[-1.480,-.259]. E4native_development nowrunning. Allcontrolsunchanged.
Profiles.py nowsetsTEARDOWN_CUPTI=0 andDISABLE_CUPTI_LAZY_REINIT=1 beforetorchimport,basedoninstalledtorch/profiler/profiler.py documentedCUDAgraphteardowncrashes; drivergraphsarenotseenbyInductorflag. Stillonly8attempts. analyze.py nowoutputscoverage.json pluspc_case_confirmation.json andpc_residual_stability.json;reportincludescase/Wsigns.

## Later update: allE4native and allE5FFN done; E5attention3 running
- FFN sixblocks180actualphases complete, fullfirstGEMM+downstreamfinalraw-bit checks passed. M/LIB GPUgain-3.478%,95%CI[-12.212,+4.967]; batch-8.623%,CI[-13.974,-3.824].M/CORE GPU+1.773%,CI[-9.574,+12.248];M/Gexact0. Stillno demonstratedcompletechainnetgain.
- AllE4native completed (development116.81s, six blocks~120s each). Eachtestblock23PASS+1NA(A035MATH);developmenthasA034MATHNA. Native isnotPCcandidate.
- Found alloldattentiondebug_dump DOTfilesmissing despitewarning. Rawtimingskeptandderivedphasesnowmarkactual_graph_artifact_statusMISSING. Reconstructed exactoriginalattention.py matchinghash4e2784908e54f8551abc6af014ce486e4a9cdff671cd421b06b964344e40d848 for allE4workers; savedfreeze/attention_original_native_epoch/attention.py andattention_metadata_epochs.json.
- Fixedfutureattentionphase: CUDAGraph(keep_graph=True), explicitinstantiateBEFOREwarmup, actualnodes/edges/kernelnamesvia checked publicdriver APIs innewsrc/graph_metadata.py. Writes*.dag.json andactual_dag inphase. No mathematicaloperation/timerchanges. E5attentionallusesnewpath. qualify_attention_dag completed4.24s, twoB4GQAchainpathsactual8and22kernels.
- Separatemetadata-onlyrecaptureauditall24actuallymeasurednativeconfigs×2backends addedunderE0(sharedlock), notnewformalbenchmark/profiler. Firstqualify_attention_metadata_all failedoncuGraphGetEdges withzerolenedgearray(singlekernelgraph); fixedskipfetchifn==0. Retryqualify_attention_metadata_all_retry01 SUCCESS10.41s,48records:46PASS,2NA(A034/A035MATH). No timingsreplaced. retrymapupdated. final_audit nowrequiresits48records andqualifiercomplete.
- package.py nowincludes*.dag.json andmetadata_audits.jsonl. report.py explainsoriginalmissingDOT vsseparaterecapture; updateanyremainingREADME DOTclaims toJSONatfinalreview. profiles.py driverGraphCUPTIteardownenvironmentfixpersists;8attemptcapunchanged.
- analyze.py nowalsoexportsphase_state_windows.jsonl withcoarse1Hzphasewindowstates (includeswarmup/checks,notperkernelclocks) andcoverage.jsonexplicitPCattentionNA. Reportnoteslengthcyclingrepresentsvaryingrequests,notmonotonicrealdecode;sourceplanmeasured=falseisfrozenoriginaldesignmetadata.
- Remainingqueue: finishE5attention sixblocks;E5ablation6,workspace4,lifetime3,E6profiles8. ThenfinalCPUanalysis/audit/plots/report/pack/commit/delivery. MainqueuePIDfromcheckpointstilldetached,readlog;don'trestartduplicate.
