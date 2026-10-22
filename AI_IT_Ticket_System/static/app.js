const $ = (id) => document.getElementById(id);
async function api(url, options={}) {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  if (!response.ok) { const data=await response.json().catch(()=>({})); throw new Error(data.detail || `Request failed (${response.status})`); }
  return response.json();
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function priorityClass(p){return p==="High"?"p-high":p==="Medium"?"p-medium":"p-low";}
function renderResult(t) {
  $("method").textContent=t.ai_method || "AI analysis";
  const similar=t.similar_tickets||[];
  $("result").className="";
  $("result").innerHTML=`
    <div class="analysis-grid">
      <div class="analysis-item"><small>Category</small><strong>${escapeHtml(t.category)}</strong></div>
      <div class="analysis-item"><small>Priority</small><strong class="${priorityClass(t.priority)}">${escapeHtml(t.priority)}</strong></div>
      <div class="analysis-item"><small>Assigned team</small><strong>${escapeHtml(t.assigned_team)}</strong></div>
    </div>
    <div class="block"><h3>Recommended resolution</h3><p>${escapeHtml(t.suggested_resolution)}</p></div>
    <div class="block"><h3>Similar historical tickets</h3>${similar.length?similar.map(s=>`<div class="similar"><strong>${escapeHtml(s.ticket_ref)} · ${escapeHtml(s.title)}</strong><small>${escapeHtml(s.category)} · similarity ${Math.round((s.similarity||0)*100)}%</small><p>${escapeHtml(s.resolution||"")}</p></div>`).join(""):"<p>No similar tickets found in the demo dataset.</p>"}</div>
    <p class="hint">Ticket #${escapeHtml(t.id)} created. AI recommendations are advisory; an engineer must review before resolution.</p>`;
}
async function loadMetrics(){
  const m=await api("/api/metrics");
  $("total").textContent=m.total;
  $("open").textContent=m.statuses["Open"]||0;
  $("progress").textContent=m.statuses["In Progress"]||0;
  $("resolved").textContent=m.statuses["Resolved"]||0;
}
async function loadTickets(){
  const tickets=await api("/api/tickets?limit=100");
  $("tickets").innerHTML=tickets.length?tickets.map(t=>`
    <tr><td>#${t.id}</td><td title="${escapeHtml(t.description)}">${escapeHtml(t.title)}</td><td>${escapeHtml(t.category)}</td>
    <td class="priority ${priorityClass(t.priority)}">${escapeHtml(t.priority)}</td><td>${escapeHtml(t.assigned_team)}</td><td>${escapeHtml(t.status)}</td>
    <td><select class="status-select" aria-label="Update status for ticket ${t.id}" onchange="updateStatus(${t.id},this.value)">
    ${["Open","In Progress","Resolved","Escalated"].map(s=>`<option ${t.status===s?"selected":""}>${s}</option>`).join("")}</select></td></tr>`).join(""):'<tr><td colspan="7">No tickets yet.</td></tr>';
}
async function refresh(){try{await Promise.all([loadMetrics(),loadTickets()]);}catch(e){console.error(e);}}
async function updateStatus(id,status){try{await api(`/api/tickets/${id}/status?status=${encodeURIComponent(status)}`,{method:"PATCH"});await refresh();}catch(e){alert(e.message);}}
$("ticket-form").addEventListener("submit",async e=>{
  e.preventDefault();const button=$("submit");button.disabled=true;button.textContent="Analyzing…";
  try{
    const t=await api("/api/tickets",{method:"POST",body:JSON.stringify({title:$("title").value.trim(),description:$("description").value.trim(),requester:$("requester").value.trim()||"Employee"})});
    renderResult(t);$("ticket-form").reset();$("requester").value="Employee";await refresh();
  }catch(err){$("result").className="empty error";$("result").textContent=err.message;}
  finally{button.disabled=false;button.textContent="Analyze & create ticket";}
});
$("refresh").addEventListener("click",refresh);
refresh();