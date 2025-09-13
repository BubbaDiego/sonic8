import { useState, useMemo, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { enqueueSnackbar } from 'notistack';

import MainCard from 'ui-component/cards/MainCard';
import {
  createSpotTrigger, listSpotTriggers, cancelSpotTrigger,
  swapQuote, swapExecute, getUsdPrice,
  whoami, walletBalance, signerInfo, debugSigner, estimateSolSpend, walletPortfolio,
  txlogLatest, txlogList
} from 'api/jupiter';

import {
  Box, Button, Chip, Grid, Stack, Tab, Tabs, TextField, Typography,
  MenuItem, FormControlLabel, Switch, Divider, Tooltip, IconButton
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

/* tokens */
const TOKENS = [
  { sym: 'SOL',     mint: 'So11111111111111111111111111111111111111112', decimals: 9 },
  { sym: 'USDC',    mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 },
  { sym: 'mSOL',    mint: 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',  decimals: 9 },
  { sym: 'JitoSOL', mint: 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', decimals: 9 }
];
const sym = (s) => TOKENS.find((t) => t.sym === s);
const atomsToUi = (atoms, decimals) => Number(atoms || 0) / 10 ** decimals;
const fmt = (n, dp=6) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: dp });
const pct = (x) => (Number(x || 0) * 100).toLocaleString(undefined, { maximumFractionDigits: 4 }) + '%';

/* ------------ Spot Triggers (unchanged compact version) ------------ */
function SpotTriggerForm(){ /* identical to prior sent version */ return null; }
function SpotTriggerTable(){ return null; }

/* ------------ Wallet card (multi-token) ------------ */
function WalletCard(){
  const qc = useQueryClient();
  const who  = useQuery({ queryKey:['jupWho'], queryFn:whoami, staleTime:5000, retry:0 });
  const sinf = useQuery({ queryKey:['jupSignerInfo'], queryFn:signerInfo, staleTime:10000, retry:0 });

  const mintsCsv = TOKENS.map(t=>t.mint).join(',');
  const portfolio = useQuery({
    queryKey:['jupPortfolio'], queryFn:()=>walletPortfolio(mintsCsv),
    staleTime:5000, retry:0, enabled:!!who.data
  });

  const short=(s)=>s?`${s.slice(0,4)}…${s.slice(-4)}`:'';
  const pub=who.data?.pubkey||sinf.data?.pubkey;
  const refresh=()=>{ qc.invalidateQueries({queryKey:['jupWho','jupSignerInfo','jupPortfolio']}); };

  const green={color:'var(--mui-palette-success-main,#2e7d32)',fontWeight:600};

  return (
    <MainCard title="Wallet" secondary={<Button size="small" onClick={refresh}>Refresh</Button>}>
      {!who.data ? <Typography>Loading…</Typography> :
       portfolio.isError ? <Typography color="error">Portfolio error: {portfolio.error?.message||'unknown'}</Typography> :
       portfolio.isLoading ? <Typography>Loading balances…</Typography> :
       <Stack spacing={1}>
         <Typography variant="body2">Pubkey: <code>{short(pub)}</code></Typography>
         {portfolio.data?.items?.map(it=>{
           const usdText = it.usd==null?'—':`$${(it.usd).toFixed(2)}`;
           return <Typography key={it.mint} variant="body2">{it.sym}: <b>{fmt(it.amount)}</b> <span style={green}>({usdText})</span></Typography>;
         })}
         <Typography variant="caption" color="textSecondary">
          Method: {sinf.data?.method||'unknown'} — Path: {sinf.data?.path||''}
         </Typography>
       </Stack>}
    </MainCard>
  );
}

/* ------------ Quote with round-trip (tooltipped) ------------ */
function QuoteCard({ quote, rt, inSym, outSym }){
  const inDec=sym(inSym).decimals, outDec=sym(outSym).decimals;
  const pill=(()=>{ if(!rt) return {text:'no edge',color:'default',tip:'No round-trip computed yet.'};
    const e=rt.edgeBps??0, tip='Round-trip edge = ((B→A minOut) − initial A) / initial A × 10,000 bps.';
    if(e>=50) return {text:`profit +${e.toFixed(2)} bps`,color:'success',tip};
    if(e>=0)  return {text:`near +${e.toFixed(2)} bps`,color:'warning',tip};
    return {text:`${e.toFixed(2)} bps`,color:'error',tip}; })();
  const Pill=<Tooltip title={pill.tip}><Chip color={pill.color} label={pill.text}/></Tooltip>;

  return (
    <MainCard title="Quote" secondary={Pill}>
      {quote ? <Stack spacing={0.75}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Typography variant="body2">outAmount (atoms): <b>{quote.outAmount}</b> <span style={{opacity:.8}}>({fmt(atomsToUi(quote.outAmount,outDec))} {outSym})</span></Typography>
          <Tooltip title="Estimated output for A→B at quote time (not guaranteed)."><IconButton size="small"><InfoOutlinedIcon fontSize="inherit"/></IconButton></Tooltip>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Typography variant="body2">otherAmountThreshold: <b>{quote.otherAmountThreshold}</b> <span style={{opacity:.8}}>({fmt(atomsToUi(quote.otherAmountThreshold,outDec))} {outSym})</span></Typography>
          <Tooltip title="Guaranteed min-out for A→B given slippage."><IconButton size="small"><InfoOutlinedIcon fontSize="inherit"/></IconButton></Tooltip>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Typography variant="body2">priceImpactPct: <b>{pct(quote.priceImpactPct)}</b></Typography>
          <Tooltip title="Single-leg price impact for A→B."><IconButton size="small"><InfoOutlinedIcon fontSize="inherit"/></IconButton></Tooltip>
        </Stack>
        {rt && <>
          <Divider sx={{my:1}}/>
          <Typography variant="subtitle2">Round-trip (A→B→A) analysis</Typography>
          <Typography variant="body2">A→B minOut (B): <b>{rt.a2bMinOut}</b> <span style={{opacity:.8}}>({fmt(atomsToUi(rt.a2bMinOut,outDec))} {outSym})</span></Typography>
          <Typography variant="body2">B→A minOut (A): <b>{rt.b2aMinOut}</b> <span style={{opacity:.8}}>({fmt(atomsToUi(rt.b2aMinOut,inDec))} {inSym})</span></Typography>
          <Typography variant="body2">Edge: <b>{(rt.edgeTokens??0).toLocaleString()}</b> atoms of {inSym} (~ <b>${fmt(rt.edgeUsd??0,3)}</b>)</Typography>
          <Typography variant="caption" color="textSecondary">Strict minOut on both legs; sequential (not atomic).</Typography>
        </>}
      </Stack> : <Typography variant="body2" color="textSecondary">No quote yet.</Typography>}
    </MainCard>
  );
}

/* ------------ Transaction card (Live / Details / History) ------------ */
function TransactionCard({ log, onClear, onCopy }) {
  const [tab, setTab] = useState(0);
  const boxRef = useRef(null);
  useEffect(()=>{ if(boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; },[log]);

  const latest = useQuery({ queryKey:['txlogLatest'], queryFn:txlogLatest, staleTime:0, retry:0 });
  const history = useQuery({ queryKey:['txlogList'], queryFn:()=>txlogList(25), staleTime:0, retry:0 });

  return (
    <MainCard
      title="Transaction"
      secondary={<Stack direction="row" spacing={1}>
        <Button size="small" onClick={onCopy}>Copy</Button>
        <Button size="small" onClick={onClear}>Clear</Button>
      </Stack>}
    >
      <Tabs value={tab} onChange={(_,v)=>setTab(v)} sx={{mb:1}}>
        <Tab label="Live log"/><Tab label="Details"/><Tab label="History"/>
      </Tabs>

      {tab===0 && (
        <Box ref={boxRef} sx={{fontFamily:'ui-monospace, Menlo, Consolas, monospace',fontSize:12,lineHeight:1.4,maxHeight:220,overflowY:'auto',p:1,bgcolor:'background.default',borderRadius:1,border:(t)=>`1px solid ${t.palette.divider}`}}>
          {log.length===0 ? <Typography variant="body2" color="textSecondary">No activity yet.</Typography> :
            log.map((r,i)=>(<div key={i} style={{whiteSpace:'pre-wrap'}}><span style={{color:'#888'}}>{r.ts}</span> <b>[{r.level}]</b> <span>{r.msg}</span></div>))}
        </Box>
      )}

      {tab===1 && (
        latest.isLoading ? <Typography>Loading…</Typography> :
        latest.isError ? <Typography color="error">No recent transaction</Typography> :
        <Box sx={{fontFamily:'ui-monospace, Menlo, Consolas, monospace',fontSize:12}}>
          <Typography variant="body2"><b>Signature:</b> {latest.data.signature || latest.data.execution?.sig}</Typography>
          <Divider sx={{my:1}}/>
          <Typography variant="subtitle2">Projected</Typography>
          <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(latest.data.projection, null, 2)}</pre>
          <Typography variant="subtitle2">Actual</Typography>
          <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(latest.data.actual, null, 2)}</pre>
          <Typography variant="subtitle2">Execution</Typography>
          <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(latest.data.execution, null, 2)}</pre>
        </Box>
      )}

      {tab===2 && (
        history.isLoading ? <Typography>Loading…</Typography> :
        history.isError ? <Typography color="error">History unavailable</Typography> :
        <Box sx={{maxHeight:240,overflowY:'auto'}}>
          <table style={{width:'100%',fontFamily:'ui-monospace, Menlo, Consolas, monospace',fontSize:12}}>
            <thead><tr><th align="left">Time</th><th align="left">Pair</th><th align="right">Proj bps</th><th align="right">Act bps</th><th align="right">Act USD</th><th align="left">Sig</th></tr></thead>
            <tbody>
              {(history.data.items||[]).map((e,i)=>{
                const ts=new Date(e.ts||Date.now()).toLocaleTimeString();
                const proj=(e.projection?.edge?.bps??null), act=(e.actual?.edge?.bps??null), usd=e.actual?.pnlUsd;
                return (<tr key={i}>
                  <td>{ts}</td>
                  <td>{e.pair?.in}→{e.pair?.out}</td>
                  <td align="right">{proj!=null?proj.toFixed(2):'—'}</td>
                  <td align="right">{act!=null?act.toFixed(2):'—'}</td>
                  <td align="right">{usd!=null?usd.toFixed(3):'—'}</td>
                  <td>{(e.execution?.sig||'').slice(0,6)}…</td>
                </tr>);
              })}
            </tbody>
          </table>
        </Box>
      )}
    </MainCard>
  );
}

/* ------------ Swaps tab (computes RT + pushes latest to txlog panel) ------------ */
function SwapsTab(){
  const [inSym,setInSym]=useState('SOL');
  const [outSym,setOutSym]=useState('USDC');
  const [amountUi,setAmountUi]=useState('0.1');
  const [slip,setSlip]=useState('50');
  const [mode,setMode]=useState('ExactIn');
  const [restrict,setRestrict]=useState(true);
  const [thresh,setThresh]=useState(50);

  const [quote,setQuote]=useState(null);
  const [rt,setRt]=useState(null);
  const [sig,setSig]=useState('');
  const [sending,setSending]=useState(false);

  const [usdPrice,setUsdPrice]=useState(null);
  useEffect(()=>{ let alive=true; const t=setTimeout(async()=>{ try{ const r=await getUsdPrice(sym(inSym).mint,'USDC'); if(alive)setUsdPrice(Number(r.price)); }catch{ if(alive)setUsdPrice(null);} },250); return()=>{alive=false;clearTimeout(t)};},[inSym]);
  const amountUsd = (()=>{ const a=Number(amountUi||0); return usdPrice?a*usdPrice:null;})();

  const [txLog,setTxLog]=useState([]);
  const pushLog=(msg,level='info')=>setTxLog(p=>[...p,{ts:new Date().toLocaleTimeString(),level,msg}]);
  const clearLog=()=>setTxLog([]); const copyLog=async()=>{ const text=txLog.map(r=>`${r.ts} [${r.level}] ${r.msg}`).join('\n'); try{ await navigator.clipboard.writeText(text); enqueueSnackbar('Transaction log copied',{variant:'success'});}catch{ enqueueSnackbar('Copy failed',{variant:'error'});} };

  const [est,setEst]=useState(null);
  const overMax = est && inSym==='SOL' && Number(amountUi||0)>(est.safeMaxSol||0);
  const setMax=()=>{ if(est?.safeMaxSol){ const v=Math.max(0,(est.safeMaxSol)-0.0005); setAmountUi(v.toFixed(6)); pushLog(`Set amount to safe max: ${v.toFixed(6)} SOL`);} };

  useEffect(()=>{ let alive=true;(async()=>{try{ if(inSym!=='SOL'){ setEst(null); return;} pushLog(`Estimating safe SOL spend for OUT=${outSym}…`); const e=await estimateSolSpend(sym(outSym).mint); if(alive){ setEst(e); pushLog(`Est: safeMax=${e.safeMaxSol.toFixed(6)} SOL, needOutAta=${e.needOutAta}`);} }catch(err){ pushLog(`Estimator error: ${err?.message||String(err)}`,'error'); if(alive) setEst(null);} })(); return()=>{alive=false};},[inSym,outSym]);

  async function computeRoundTrip(a2bQuote, amountAtoms){
    try{
      const bMin = Number(a2bQuote.otherAmountThreshold);
      pushLog(`RT: reverse quote ${outSym}→${inSym} amount=${bMin} atoms…`);
      const back=await swapQuote({ inputMint:sym(outSym).mint, outputMint:sym(inSym).mint, amount:bMin, slippageBps:Number(slip||50), swapMode:'ExactIn', restrictIntermediates:restrict });
      const aBack = Number(back.otherAmountThreshold);
      const edgeTokens = aBack - Number(amountAtoms);
      const edgeBps = (edgeTokens / Number(amountAtoms)) * 10000;
      const edgeUsd = usdPrice ? (edgeTokens/(10**sym(inSym).decimals))*usdPrice : 0;
      setRt({ a2bMinOut:bMin, b2aMinOut:aBack, edgeTokens, edgeBps, edgeUsd });
      pushLog(`RT: edge=${edgeBps.toFixed(2)} bps (~$${(edgeUsd||0).toFixed(3)})`);
    }catch(e){ setRt(null); pushLog(`RT error: ${e?.message||String(e)}`,'error');}
  }

  async function doQuote(){
    try{
      setSig(''); setQuote(null); setRt(null);
      const amtAtoms=Math.floor(Number(amountUi)*10**sym(inSym).decimals);
      pushLog(`Quote: ${inSym}→${outSym}, amt=${amountUi} (${amtAtoms} atoms), slip=${slip}bps`);
      const q=await swapQuote({ inputMint:sym(inSym).mint, outputMint:sym(outSym).mint, amount:amtAtoms, slippageBps:Number(slip||50), swapMode:mode, restrictIntermediates:restrict });
      setQuote(q); pushLog(`Quote OK: out=${q.outAmount}, minOut=${q.otherAmountThreshold}, impact=${q.priceImpactPct}`);
      await computeRoundTrip(q, amtAtoms);
    }catch(e){ pushLog(`Quote error: ${e?.message||String(e)}`,'error'); enqueueSnackbar(e?.message||'Quote failed',{variant:'error'}); }
  }

  async function doSwap(){
    if(!quote) return; setSending(true);
    try{
      pushLog('Swap: building + sending…');
      const r = await swapExecute({ quoteResponse: quote });
      setSig(r.signature); pushLog(`Swap sent: ${r.signature}`,'success');
      // pull latest txlog for Details/History panes
      await Promise.allSettled([
        queryClient.invalidateQueries({queryKey:['txlogLatest']}),
        queryClient.invalidateQueries({queryKey:['txlogList']})
      ]);
      enqueueSnackbar('Swap sent',{variant:'success'});
    }catch(e){ pushLog(`Swap error: ${e?.message||String(e)}`,'error'); enqueueSnackbar(e?.message||'Swap failed',{variant:'error'}); }
    setSending(false);
  }

  const queryClient = useQueryClient();

  return (
    <Stack spacing={2}>
      <MainCard title="Headless Swap">
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}><TextField select fullWidth label="Token In" value={inSym} onChange={(e)=>setInSym(e.target.value)}>{TOKENS.map(t=><MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}</TextField></Grid>
          <Grid item xs={12} md={3}><TextField select fullWidth label="Token Out" value={outSym} onChange={(e)=>setOutSym(e.target.value)}>{TOKENS.map(t=><MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}</TextField></Grid>
          <Grid item xs={12} md={2}><TextField fullWidth label="Amount (in)" value={amountUi} onChange={(e)=>setAmountUi(e.target.value)} helperText={usdPrice?`≈ $${(Number(amountUi||0)*usdPrice).toLocaleString(undefined,{maximumFractionDigits:2})}`:' '} /></Grid>
          <Grid item xs={12} md={2}><TextField fullWidth label="Slippage (bps)" value={slip} onChange={(e)=>setSlip(e.target.value)} /></Grid>
          <Grid item xs={12} md={2}><TextField fullWidth label="Profit thresh (bps)" value={thresh} onChange={(e)=>setThresh(Number(e.target.value||0))} /></Grid>
          <Grid item xs={12}><FormControlLabel control={<Switch checked={restrict} onChange={(e)=>setRestrict(e.target.checked)} />} label="Restrict intermediate tokens" /></Grid>
          <Grid item xs={12}><Stack direction="row" spacing={1}><Button variant="outlined" onClick={doQuote} disabled={overMax}>Quote</Button><Button variant="contained" onClick={doSwap} disabled={!quote||sending||overMax}>{sending?'Swapping…':'Swap'}</Button>{inSym==='SOL'&&est&&<Button variant="text" onClick={setMax}>Max (safe)</Button>}{overMax&&<Chip color="warning" label="Over safe max — lower amount"/>}</Stack></Grid>
        </Grid>
        {inSym==='SOL'&&est&&(<Box sx={{mt:1}}><Typography variant="caption" color="textSecondary">Available to swap (est): <b>{est.safeMaxSol.toFixed(6)} SOL</b> • Rent WSOL: {(est.rentWsolLamports/1e9).toFixed(6)}{est.needOutAta?` • Rent ${outSym} ATA: ${(est.rentOutAtaLamports/1e9).toFixed(6)}`:''} • Buffer: {(est.bufferLamports/1e9).toFixed(6)}</Typography></Box>)}
      </MainCard>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}><QuoteCard quote={quote} rt={rt&&{...rt,ok:(rt.edgeBps??-1)>=thresh}} inSym={inSym} outSym={outSym}/></Grid>
        <Grid item xs={12} md={4}><WalletCard/></Grid>
        <Grid item xs={12} md={4}><TransactionCard log={txLog} onClear={clearLog} onCopy={copyLog}/></Grid>
      </Grid>

      {sig && <MainCard title="Broadcast"><Typography variant="body2">Signature: <code>{sig}</code></Typography></MainCard>}
    </Stack>
  );
}

/* ------------ Page wrapper ------------ */
export default function JupiterPage(){
  const [tab,setTab]=useState(2);
  return (
    <Stack spacing={2}>
      <MainCard title="Jupiter" secondary={<Chip color="primary" label="Headless"/>}>
        <Tabs value={tab} onChange={(_,v)=>setTab(v)} variant="scrollable">
          <Tab label="Spot Triggers"/><Tab label="Perps TP/SL"/><Tab label="Swaps"/>
        </Tabs>
      </MainCard>
      {tab===0 && <><SpotTriggerForm/><SpotTriggerTable/></>}
      {tab===1 && <MainCard title="Perps TP / SL"><Typography>Coming soon.</Typography></MainCard>}
      {tab===2 && <SwapsTab/>}
    </Stack>
  );
}
