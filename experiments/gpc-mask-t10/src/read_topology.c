/* Read-only topology queries. No hardware register writes or SET controls.
 * ABI comes from NVIDIA open-gpu-kernel-modules tag 580.178.04.
 * RM allocation/free below only creates/destroys this process's query handles.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include "nvos.h"
#include "class/cl0041.h"
#include "class/cl0080.h"
#include "class/cl2080.h"
#include "ctrl/ctrl0000/ctrl0000gpu.h"
#include "ctrl/ctrl2080/ctrl2080gr.h"
#include "ctrl/ctrl2080/ctrl2080grmgr.h"
#include "nv_escape.h"
static int fd;
static NvHandle root;
static int call(unsigned nr, void *p, size_t n) {
 int rc=ioctl(fd,_IOC(_IOC_READ|_IOC_WRITE,'F',nr,n),p);
 if(rc<0) {fprintf(stderr,"ioctl nr=%x size=%zu errno=%d %s\n",nr,n,errno,strerror(errno));exit(2);}
 return rc;
}
static void alloc(NvHandle parent,NvHandle *obj,unsigned cls,void *p,unsigned n) {
 NVOS21_PARAMETERS a={0};a.hRoot=root;a.hObjectParent=parent;a.hObjectNew=*obj;a.hClass=cls;a.pAllocParms=p;a.paramsSize=n;
 call(NV_ESC_RM_ALLOC,&a,sizeof(a));
 fprintf(stderr,"alloc class=%x status=%x handle=%x\n",cls,a.status,a.hObjectNew);
 if(a.status) exit(3);
 *obj=a.hObjectNew;
}
static unsigned ctrl(NvHandle obj,unsigned cmd,void *p,unsigned n) {
 NVOS54_PARAMETERS a={0};a.hClient=root;a.hObject=obj;a.cmd=cmd;a.params=p;a.paramsSize=n;
 call(NV_ESC_RM_CONTROL,&a,sizeof(a));
 fprintf(stderr,"get cmd=%x size=%u status=%x\n",cmd,n,a.status);return a.status;
}
#define GET(obj,cmd,p) ctrl(obj,cmd,&p,sizeof(p))
int main(void) {
 setbuf(stdout,NULL);
 fd=open("/dev/nvidiactl",O_RDWR|O_CLOEXEC);if(fd<0){perror("open ctl");return 1;}
 int gpu=open("/dev/nvidia0",O_RDWR|O_CLOEXEC);if(gpu<0){perror("open gpu");return 1;}
 alloc(0,&root,NV01_ROOT_CLIENT,NULL,0);
 NV0000_CTRL_GPU_GET_ATTACHED_IDS_PARAMS ids={0};
 if(GET(root,NV0000_CTRL_CMD_GPU_GET_ATTACHED_IDS,ids))return 4;
 unsigned count=0;while(count<32 && ids.gpuIds[count]!=NV0000_CTRL_GPU_INVALID_ID)count++;
 if(count!=1){fprintf(stderr,"Expected exactly one GPU, got %u\n",count);return 4;}
 NV0000_CTRL_GPU_GET_ID_INFO_V2_PARAMS id={0};id.gpuId=ids.gpuIds[0];
 if(GET(root,NV0000_CTRL_CMD_GPU_GET_ID_INFO_V2,id))return 4;
 printf("{\"gpu_id\":%u,\"device_instance\":%u,\"gpu_instance\":%u,",id.gpuId,id.deviceInstance,id.gpuInstance);
 NV0080_ALLOC_PARAMETERS dp={0};dp.deviceId=id.deviceInstance;
 NvHandle dev=0x100;alloc(root,&dev,NV01_DEVICE_0,&dp,sizeof(dp));
 NV2080_ALLOC_PARAMETERS sp={0};sp.subDeviceId=id.subDeviceInstance;
 NvHandle sub=0x101;alloc(dev,&sub,NV20_SUBDEVICE_0,&sp,sizeof(sp));
 NV2080_CTRL_GR_INFO vals[]={
 {NV2080_CTRL_GR_INFO_INDEX_LITTER_NUM_GPCS,0},
 {NV2080_CTRL_GR_INFO_INDEX_LITTER_NUM_TPC_PER_GPC,0},
 {NV2080_CTRL_GR_INFO_INDEX_LITTER_NUM_SM_PER_TPC,0},
 {NV2080_CTRL_GR_INFO_INDEX_SHADER_PIPE_COUNT,0},
 {NV2080_CTRL_GR_INFO_INDEX_SHADER_PIPE_SUB_COUNT,0}};
 NV2080_CTRL_GR_GET_INFO_PARAMS gi={0};gi.grInfoListSize=5;gi.grInfoList=vals;
 unsigned st=GET(sub,NV2080_CTRL_CMD_GR_GET_INFO,gi);
 printf("\"gr_info\":{\"status\":%u,\"values\":[",st);
 for(int i=0;i<5;i++)printf("%s{\"index\":%u,\"value\":%u}",i?",":"",vals[i].index,vals[i].data);
 printf("]},");
 NV2080_CTRL_GR_GET_GPC_MASK_PARAMS gm={0};st=GET(sub,NV2080_CTRL_CMD_GR_GET_GPC_MASK,gm);
 printf("\"gpc_mask\":{\"status\":%u,\"mask\":%u},",st,gm.gpcMask);
 NV2080_CTRL_GR_GET_PHYS_GPC_MASK_PARAMS pm={0};st=GET(sub,NV2080_CTRL_CMD_GR_GET_PHYS_GPC_MASK,pm);
 printf("\"phys_gpc_mask\":{\"status\":%u,\"mask\":%u},",st,pm.gpcMask);
 unsigned ng=vals[0].data;if(ng==0||ng>32)return 5;
 printf("\"tpc_masks\":[");
 for(unsigned i=0;i<ng;i++) {NV2080_CTRL_GR_GET_TPC_MASK_PARAMS tm={0};tm.gpcId=i;st=GET(sub,NV2080_CTRL_CMD_GR_GET_TPC_MASK,tm);printf("%s{\"physical_gpc\":%u,\"status\":%u,\"mask\":%u}",i?",":"",i,st,tm.tpcMask);}
 printf("],");
 NV2080_CTRL_GRMGR_GET_GR_FS_INFO_PARAMS fs={0};
 fs.numQueries=1;fs.queries[0].queryType=NV2080_CTRL_GRMGR_GR_FS_INFO_QUERY_GPC_COUNT;
 unsigned active=__builtin_popcount(gm.gpcMask);
 for(unsigned i=0;i<active;i++) {
  unsigned j=fs.numQueries++;
  fs.queries[j].queryType=NV2080_CTRL_GRMGR_GR_FS_INFO_QUERY_CHIPLET_GPC_MAP;
  fs.queries[j].queryData.chipletGpcMapData.gpcId=i;
  j=fs.numQueries++;
  fs.queries[j].queryType=NV2080_CTRL_GRMGR_GR_FS_INFO_QUERY_TPC_MASK;
  fs.queries[j].queryData.tpcMaskData.gpcId=i;
 }
 st=GET(sub,NV2080_CTRL_CMD_GRMGR_GET_GR_FS_INFO,fs);
 printf("\"floor_sweep_info\":{\"status\":%u,\"count_status\":%u,\"gpc_count\":%u,\"entries\":[",st,fs.queries[0].status,fs.queries[0].queryData.gpcCountData.gpcCount);
 for(unsigned i=0;i<active;i++) {
  unsigned j=1+2*i,k=j+1;
  printf("%s{\"logical_gpc\":%u,\"map_status\":%u,\"physical_gpc\":%u,\"tpc_status\":%u,\"physical_tpc_mask\":%u}",i?",":"",i,fs.queries[j].status,fs.queries[j].queryData.chipletGpcMapData.chipletGpcMap,fs.queries[k].status,fs.queries[k].queryData.tpcMaskData.tpcMask);
 }
 printf("]},");
 NV2080_CTRL_GR_GET_SM_TO_GPC_TPC_MAPPINGS_PARAMS sm={0};st=GET(sub,NV2080_CTRL_CMD_GR_GET_SM_TO_GPC_TPC_MAPPINGS,sm);
 printf("\"sm_mapping\":{\"status\":%u,\"count\":%u,\"entries\":[",st,sm.smCount);
 if(sm.smCount>240)return 5;
 for(unsigned i=0;i<sm.smCount;i++)printf("%s{\"sm\":%u,\"gpc\":%u,\"tpc\":%u}",i?",":"",i,sm.smId[i].gpcId,sm.smId[i].tpcId);
 printf("]},");
 NV2080_CTRL_GR_GET_GLOBAL_SM_ORDER_PARAMS go={0};st=GET(sub,NV2080_CTRL_CMD_GR_GET_GLOBAL_SM_ORDER,go);
 printf("\"global_sm_order\":{\"status\":%u,\"num_sm\":%u,\"num_tpc\":%u,\"entries\":[",st,go.numSm,go.numTpc);
 if(go.numSm>512)return 5;
 for(unsigned i=0;i<go.numSm;i++)printf("%s{\"sm\":%u,\"gpc\":%u,\"local_tpc\":%u,\"local_sm\":%u,\"global_tpc\":%u,\"virtual_gpc\":%u,\"migratable_tpc\":%u,\"ugpu\":%u,\"physical_cpc\":%u,\"virtual_tpc\":%u}",i?",":"",i,go.globalSmId[i].gpcId,go.globalSmId[i].localTpcId,go.globalSmId[i].localSmId,go.globalSmId[i].globalTpcId,go.globalSmId[i].virtualGpcId,go.globalSmId[i].migratableTpcId,go.globalSmId[i].ugpuId,go.globalSmId[i].physicalCpcId,go.globalSmId[i].virtualTpcId);
 printf("]}}");
 NVOS00_PARAMETERS f={0};f.hRoot=root;f.hObjectOld=root;call(NV_ESC_RM_FREE,&f,sizeof(f));
 fprintf(stderr,"free root status=%x\n",f.status);close(gpu);close(fd);return f.status?6:0;
}
