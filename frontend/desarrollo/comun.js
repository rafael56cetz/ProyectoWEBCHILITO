// Synthetic responses for the single frontend. No transport or persistent storage.
const FrontendDevelopment = (() => {
  const scenarios={auth:'verified-session',privacy:'ready',security:'ready'};
  const pause=(signal,delay=400)=>new Promise((resolve,reject)=>{
    if(signal?.aborted){reject(new DOMException('Cancelled','AbortError'));return;}
    const abort=()=>{clearTimeout(timer);reject(new DOMException('Cancelled','AbortError'));};
    const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},delay);
    signal?.addEventListener('abort',abort,{once:true});
  });
  return {scenarios,pause};
})();
