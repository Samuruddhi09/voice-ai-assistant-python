import { db } from "./firebase.js";
import { doc, setDoc } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// Backend URL
const API = "http://127.0.0.1:5000";

// Sounds
const clickSound = new Audio("/static/sounds/clicksound.weba");
const startSound = new Audio("/static/sounds/startsound.wav");

// Voice memory
let lastBotMessage = "";
let isSpeakingPaused = false;

// Voice buttons
const toggleBtn = document.getElementById("toggleVoiceBtn");
const toggleIcon = document.getElementById("voiceToggleIcon");
const replayBtn   = document.getElementById("replayBtn");

function playClick(){ clickSound.currentTime=0; clickSound.play(); }
function playStart(){ startSound.currentTime=0; startSound.play(); }

// Note triggers
const noteTriggers = ["note that","take a note","make a note","note this","remember this","remember that","save this note"];

function extractNote(text){
  const lower=text.toLowerCase();
  for(const t of noteTriggers){
    if(lower.startsWith(t)) return text.slice(t.length).trim();
    if(lower.includes(t)) return text.split(t)[1].trim();
  }
  return null;
}

// Chat memory
let chatLog = {};
let sessionId = localStorage.getItem("chatSessionId");
try{ chatLog = JSON.parse(localStorage.getItem("chatLog")) || {}; }catch{}
if(!sessionId){
  sessionId = Date.now().toString();
  localStorage.setItem("chatSessionId",sessionId);
}
chatLog[sessionId] = chatLog[sessionId] || [];

// DOM
const chatInput = document.getElementById("chatbox");
const sendIcon = document.getElementById("sendIcon");
const micButton = document.getElementById("MicBtn");
const chatContainer = document.getElementById("chat-messages");
const historyContainer = document.getElementById("chat-history-list");
const bunnyAvatar = document.querySelector(".bunny-avatar");

// Voice setup
let selectedVoice=null;
function loadVoices(){
  const voices=speechSynthesis.getVoices();
  selectedVoice = voices.find(v=>v.name==="Google UK English Female") ||
                   voices.find(v=>v.lang.startsWith("en") && v.name.toLowerCase().includes("female")) ||
                   voices.find(v=>v.lang.startsWith("en")) ||
                   voices[0];
}
window.speechSynthesis.onvoiceschanged=loadVoices; loadVoices();

function speak(text){
  lastBotMessage = text;
  const utt=new SpeechSynthesisUtterance(text);
  utt.voice = selectedVoice; utt.pitch=1; utt.rate=1;
  speechSynthesis.speak(utt);
  bunnyAvatar?.classList.add("pulsing");
  utt.onend=()=>bunnyAvatar?.classList.remove("pulsing");
}

// Pause / Resume voice
toggleBtn?.addEventListener("click",() => {
  if(!speechSynthesis.speaking) return;
  if(!isSpeakingPaused){
    speechSynthesis.pause();
    isSpeakingPaused=true;
    toggleIcon.className="bi bi-play-circle";
  }else{
    speechSynthesis.resume();
    isSpeakingPaused=false;
    toggleIcon.className="bi bi-pause-circle";
  }
});

// Replay voice
replayBtn?.addEventListener("click",()=>{
  if(lastBotMessage) speak(lastBotMessage);
});

// Speech to text
let recognition,recognitionActive=false;
if("webkitSpeechRecognition" in window){
  recognition = new webkitSpeechRecognition();
  recognition.continuous=true;
  recognition.interimResults=false;
  recognition.lang="en-US";
  recognition.onresult=e=>processChat(e.results[e.results.length-1][0].transcript.trim());
  recognition.onend=()=> recognitionActive && recognition.start();
  micButton?.addEventListener("click",()=>{ playClick(); recognitionActive?stopMic():startMic(); });
}else micButton?.setAttribute("disabled",true);

function startMic(){
  if(!recognitionActive && recognition && !speechSynthesis.speaking){
    playStart(); recognition.start();
    recognitionActive=true; micButton.classList.add("listening");
    bunnyAvatar?.classList.add("pulsing");
  }
}
function stopMic(){
  if(recognitionActive && recognition){
    recognition.stop(); recognitionActive=false;
    micButton.classList.remove("listening");
    bunnyAvatar?.classList.remove("pulsing");
  }
}

// Send text input
chatInput?.addEventListener("keypress",e=>{
  if(e.key==="Enter" && chatInput.value.trim()){
    playClick(); processChat(chatInput.value.trim());
  }
});
sendIcon?.addEventListener("click",()=>{
  if(chatInput.value.trim()){
    playClick(); processChat(chatInput.value.trim());
  }
});

// Process user message
function processChat(message){
  addMessage("user",message);
  chatInput.value=""; const lower=message.toLowerCase().trim();
  bunnyAvatar?.classList.add("pulsing");

  // Greeting
  if(["hi","hello","hey","hi bunny","hello bunny","hey bunny"].includes(lower)){
    const g = ["Hi!","Hello friend ","Hey there! "];
    return botSay(g[Math.floor(Math.random()*g.length)]);
  }

  // Notes
  const possibleNote = extractNote(message);
  if(possibleNote){
    saveNoteFromChat(possibleNote);
    return botSay("Noted");
  }

  // Apps
  if(lower.startsWith("open ")){
    const appName=lower.replace("open ","").trim();
    fetch(`${API}/launch-app`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({app:appName})})
      .then(r=>r.json()).then(res=>botSay(res.success?`Opening ${appName}`:`Can't open ${appName}`));
    return;
  }

  // YouTube
  if(lower.includes("youtube")){
    const isPlay=lower.includes("play");
    const query=lower.replace(/(play|search|on)?\s*youtube/g,"").trim();
    if(!query) return botSay(isPlay?"What to play?":"What to search?");
    const url = isPlay?`${API}/youtube/play?q=${query}`:`${API}/youtube/search?q=${query}`;
    return fetch(url).then(r=>r.json()).then(()=>botSay(`${isPlay?"Playing":"Searching"} ${query}`));
  }

  // Google
  if(["search","find","google"].some(t=>lower.includes(t))){
    const q=message.replace(/(search|find|google)/i,"").trim();
    window.open(`https://www.google.com/search?q=${encodeURIComponent(q)}`);
    return botSay(`Searching for "${q}"`);
  }

  // Time
  if(lower.includes("time in")){
    const c=lower.split("time in")[1].trim();
    return fetch(`${API}/time/${c}`).then(r=>r.json()).then(d=>botSay(d.time||"Time error"));
  }
  if(lower.includes("time"))
    return fetch(`${API}/time`).then(r=>r.json()).then(d=>botSay(d.time));

  // Forex session
  if(lower.includes("session"))
    return fetch(`${API}/trading-session`).then(r=>r.json()).then(d=>botSay(d.session));

  // Gold
  if(lower.includes("gold")) return getGoldSignal();

  // Stock advisor voice
  if(lower.includes("stock")||lower.includes("market")){
    let duration="1day",capital=20000,risk="low",top_n=5;
    if(lower.includes("month")) duration="1month";
    if(lower.includes("week")) duration="1week";
    if(lower.includes("3 months")) duration="3months";
    if(lower.includes("15 days")) duration="15days";

    const m=lower.match(/(\d+)(k)?/);
    if(m) capital = m[2]?Number(m[1])*1000:Number(m[1]);

    botSay(" Analyzing stocks...");
    fetch(`${API}/api/stock-advice?duration=${duration}&capital=${capital}&risk=${risk}&top_n=${top_n}`)
      .then(r=>r.json()).then(data=>{
        if(!data.length) return botSay("No suggestions now.");
        let msg=`Best stocks:\n`;
        data.forEach(s=> msg+=` ${s.Stock} — ₹${s.Price} — ${s["Expected Return (%)"]}%\n`);
        botSay(msg);
      });
    return;
  }

  botSay("I'm still learning. Try something else!");
}

// Bot reply helper
function botSay(text){ addMessage("bot",text); speak(text); bunnyAvatar?.classList.remove("pulsing"); }

// Gold Signal
function getGoldSignal(){
  botSay("Checking gold...");
  fetch(`${API}/gold-signal`).then(r=>r.json()).then(d=>{
    botSay(`Gold: ${d.signal||"No signal"} | Price ${d.price}`);
  });
}

// Save note
async function saveNoteFromChat(text){
  try{
    const id=crypto.randomUUID();
    const data={id,title:text.slice(0,40)||"Note",body:text,createdAt:new Date(),updatedAt:new Date()};
    const user=window.auth?.currentUser;
    if(user && db) await setDoc(doc(db,"users",user.uid,"notes",id),data);
    else{
      let list=JSON.parse(localStorage.getItem("bunny_notes_local")||"[]");
      list.unshift(data); localStorage.setItem("bunny_notes_local",JSON.stringify(list));
    }
  }catch(e){console.error(e);}
}

// Chat system
async function addMessage(sender,message){
  const time=new Date().toISOString();
  chatLog[sessionId].push({sender,message,time});
  localStorage.setItem("chatLog",JSON.stringify(chatLog));
  renderMessage(sender,message);
  try{await setDoc(doc(db,"chats",sessionId),{messages:chatLog[sessionId]});}catch{}
}
function renderMessage(sender,message){
  const div=document.createElement("div");
  div.className=`chat-bubble ${sender}`; div.textContent=message;
  chatContainer.appendChild(div); chatContainer.scrollTop=chatContainer.scrollHeight;
}
function renderChatHistory(){
  if(!historyContainer) return;
  const stored=JSON.parse(localStorage.getItem("chatLog"))||{};
  historyContainer.innerHTML="";
  Object.entries(stored).forEach(([id,msgs])=>{
    const txt=msgs[0]?.message?.slice(0,30)||"New Chat";
    const a=document.createElement("a");
    a.href=`/?session=${id}`;
    a.className="list-group-item bg-dark text-white";
    a.textContent=txt; historyContainer.appendChild(a);
  });
}

// New chat
window.startNewChat=function(){
  localStorage.setItem("chatLog",JSON.stringify(chatLog));
  sessionId=Date.now().toString(); chatLog[sessionId]=[];
  localStorage.setItem("chatSessionId",sessionId);
  chatContainer.innerHTML=""; renderChatHistory();
  botSay("New chat started!");
};

// Startup greeting
function greetUser(){
  botSay("Hello! I'm Dear Bunny, How can I help you?");
  setTimeout(startMic,600);
}

window.addEventListener("DOMContentLoaded",()=>{
  const param=new URLSearchParams(window.location.search).get("session");
  if(param){sessionId=param; chatLog[sessionId] ||= []; localStorage.setItem("chatSessionId",sessionId);}
  (chatLog[sessionId]||[]).forEach(m=>renderMessage(m.sender,m.message));
  renderChatHistory(); setTimeout(greetUser,800);
});
