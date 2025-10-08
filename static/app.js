const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let currentClassFilter = '';

function resetForm(){
	$('#student-id').value = '';
	$('#class_name').value = '';
	$('#student_name').value = '';
	$('#father_name').value = '';
	$('#parent_phone').value = '';
	$('#monthly_fee').value = '';
}

async function loadClasses(){
	const res = await fetch('/api/classes');
	const classes = await res.json();
	const ul = $('#class-list');
	ul.innerHTML = '';
	const all = document.createElement('li');
	all.innerHTML = `<button class="link ${currentClassFilter?'':'active'}" data-class="">All</button>`;
	ul.appendChild(all);
	for(const c of classes){
		const li = document.createElement('li');
		li.innerHTML = `
			<div style="display:flex; gap:8px; align-items:center;">
				<button class="link ${currentClassFilter===c?'active':''}" data-class="${c}">${c}</button>
				<button class="danger" data-delete-class="${c}">Delete</button>
			</div>`;
		ul.appendChild(li);
	}
	ul.onclick = async (e)=>{
		const del = e.target.closest('button[data-delete-class]');
		if(del){
			const name = del.getAttribute('data-delete-class');
			if(confirm(`Delete class "${name}" and all its students and payments?`)){
				await fetch(`/api/classes/${encodeURIComponent(name)}`, { method:'DELETE' });
				currentClassFilter = '';
				await Promise.all([loadClasses(), loadStudents()]);
			}
			return;
		}
		const b = e.target.closest('button[data-class]');
		if(!b) return;
		currentClassFilter = b.getAttribute('data-class');
		$$('#class-list .link').forEach(x=>x.classList.remove('active'));
		b.classList.add('active');
		loadStudents();
	};
}

async function loadStudents(){
	const qs = currentClassFilter ? `?class=${encodeURIComponent(currentClassFilter)}` : '';
	const res = await fetch('/api/students'+qs);
	const students = await res.json();
	const tbody = $('#students-table tbody');
	tbody.innerHTML = '';
	for(const s of students){
		const tr = document.createElement('tr');
		const cells = [
			String(s.id),
			s.class_name,
			s.student_name,
			s.father_name || '-',
			s.parent_phone || '-',
			String(s.monthly_fee)
		];
		cells.forEach((val)=>{
			const td = document.createElement('td');
			td.textContent = val;
			tr.appendChild(td);
		});
		const actions = document.createElement('td');
		actions.innerHTML = `
			<button data-edit="${s.id}">Edit</button>
			<button data-delete="${s.id}">Delete</button>
			<button data-pay="${s.id}">Payments</button>
			<button data-quickpay="${s.id}">Quick Pay</button>
			<button data-print="${s.id}">Print Slip</button>
			<button data-notify="${s.id}">WhatsApp</button>`;
		tr.appendChild(actions);
		tbody.appendChild(tr);
	}
}

function openPaymentsDialog(student){
	const overlay = document.createElement('div');
	overlay.className = 'overlay';
	const dialog = document.createElement('div');
	dialog.className = 'dialog';
	dialog.innerHTML = `
		<h3>Payments - ${student.student_name}</h3>
		<table class="payments">
			<thead><tr><th>Month</th><th>Amount</th><th>Paid</th><th>Carry Forward Due</th></tr></thead>
			<tbody></tbody>
		</table>
		<div class="dialog-actions">
			<button id="close-dialog">Close</button>
		</div>`;
	overlay.appendChild(dialog);
	document.body.appendChild(overlay);
	$('#close-dialog').onclick = ()=> overlay.remove();

	fetch(`/api/students/${student.id}/payments`).then(r=>r.json()).then(data=>{
		const tbody = dialog.querySelector('tbody');
		months.forEach((m,idx)=>{
			const row = document.createElement('tr');
			const tdMonth = document.createElement('td'); tdMonth.textContent = m; row.appendChild(tdMonth);
			const tdAmount = document.createElement('td');
			const input = document.createElement('input'); input.type='number'; input.min='0'; input.value = data[idx]?.amount || 0; input.setAttribute('data-month', String(idx)); input.style.width='100px';
			tdAmount.appendChild(input); row.appendChild(tdAmount);
			const tdPaid = document.createElement('td'); tdPaid.textContent = (data[idx]?.amount||0) > 0 ? 'Yes' : 'No'; row.appendChild(tdPaid);
			const tdDue = document.createElement('td'); tdDue.textContent = String(data[idx]?.carry_forward_due ?? 0); row.appendChild(tdDue);
			tbody.appendChild(row);
		});
		tbody.addEventListener('change', async (e)=>{
			if(e.target.matches('input[type="number"]')){
				const month_index = Number(e.target.getAttribute('data-month'));
				const amount = Number(e.target.value);
				await fetch(`/api/students/${student.id}/payments`, {
					method: 'POST', headers: {'Content-Type': 'application/json'},
					body: JSON.stringify({ month_index, amount })
				});
				const cell = e.target.parentElement.nextElementSibling;
				cell.textContent = amount > 0 ? 'Yes' : 'No';
				const res = await fetch(`/api/students/${student.id}/payments`);
				const fresh = await res.json();
				e.target.closest('tr').querySelectorAll('td')[3].textContent = fresh[month_index]?.carry_forward_due ?? 0;
			}
		});
	});
}

function fillForm(s){
	$('#student-id').value = s.id;
	$('#class_name').value = s.class_name;
	$('#student_name').value = s.student_name;
	$('#father_name').value = s.father_name || '';
	$('#parent_phone').value = s.parent_phone || '';
	$('#monthly_fee').value = s.monthly_fee;
}

async function getStudent(id){
	const qs = currentClassFilter ? `?class=${encodeURIComponent(currentClassFilter)}` : '';
	const res = await fetch('/api/students'+qs);
	const all = await res.json();
	return all.find(x=>x.id===id);
}

function attachTableActions(){
	$('#students-table').addEventListener('click', async (e)=>{
		const btn = e.target.closest('button');
		if(!btn) return;
		const id = Number(btn.getAttribute('data-edit')||btn.getAttribute('data-delete')||btn.getAttribute('data-pay')||btn.getAttribute('data-quickpay')||btn.getAttribute('data-print')||btn.getAttribute('data-notify'));
		if(btn.hasAttribute('data-edit')){
			const s = await getStudent(id);
			if(s) fillForm(s);
		}
		if(btn.hasAttribute('data-delete')){
			if(confirm('Delete this student?')){
				await fetch(`/api/students/${id}`, { method: 'DELETE' });
				await loadStudents();
			}
		}
		if(btn.hasAttribute('data-pay')){
			const s = await getStudent(id);
			if(s) openPaymentsDialog(s);
		}
		if(btn.hasAttribute('data-quickpay')){
			const s = await getStudent(id);
			if(!s) return;
			const monthPrompt = prompt('Enter month (0-11 where 0=January, 11=December):');
			if(monthPrompt===null) return;
			const month_index = Number(monthPrompt);
			if(Number.isNaN(month_index) || month_index<0 || month_index>11){ alert('Invalid month'); return; }
			const amountPrompt = prompt(`Enter amount for ${months[month_index]}:`, String(s.monthly_fee||0));
			if(amountPrompt===null) return;
			const amount = Number(amountPrompt);
			if(Number.isNaN(amount) || amount<0){ alert('Invalid amount'); return; }
			await fetch(`/api/students/${s.id}/payments`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ month_index, amount }) });
			alert('Payment saved');
		}
		if(btn.hasAttribute('data-print')){
			openPrintDialog(id);
		}
		if(btn.hasAttribute('data-notify')){
			const s = await getStudent(id);
			const msg = prompt('Message to send via WhatsApp:', `Fee update for ${s.student_name} (Class ${s.class_name}).`);
			if(msg!=null){
				const r = await fetch(`/api/notify/${id}`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({message: msg}) });
				const out = await r.json();
				alert(`Status: ${out.status} -> ${out.to}`);
			}
		}
	});
}

function attachForm(){
	$('#student-form').addEventListener('submit', async (e)=>{
		e.preventDefault();
		if(!$('#class_name').value.trim() || !$('#student_name').value.trim() || !$('#father_name').value.trim()){
			alert('Please fill Class, Student Name, Father Name');
			return;
		}
		const payload = {
			class_name: $('#class_name').value.trim(),
			student_name: $('#student_name').value.trim(),
			father_name: $('#father_name').value.trim(),
			parent_phone: $('#parent_phone').value.trim(),
			monthly_fee: Number($('#monthly_fee').value)
		};
		const id = $('#student-id').value.trim();
		if(id){
			await fetch(`/api/students/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
		}else{
			await fetch(`/api/students`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
		}
		resetForm();
		await Promise.all([loadStudents(), loadClasses()]);
	});
	$('#reset').addEventListener('click', (e)=>{ e.preventDefault(); resetForm(); });
	$('#refresh').addEventListener('click', async ()=>{ await Promise.all([loadStudents(), loadClasses()]); });
}

function openPrintDialog(studentId){
	const overlay = document.createElement('div');
	overlay.className = 'overlay';
	const dialog = document.createElement('div');
	dialog.className = 'dialog';
	dialog.innerHTML = `
		<h3>Select Month to Print</h3>
		<div class="row">
			<label>Month</label>
			<select id="dlg-month">${months.map((m,i)=>`<option value="${i}">${m}</option>`).join('')}</select>
		</div>
		<div class="dialog-actions">
			<button id="dlg-cancel">Cancel</button>
			<button id="dlg-print">Continue</button>
		</div>`;
	overlay.appendChild(dialog);
	document.body.appendChild(overlay);
	$('#dlg-cancel').onclick = ()=> overlay.remove();
	$('#dlg-print').onclick = ()=>{
		const idx = Number($('#dlg-month').value);
		window.location.href = `/print/${studentId}?month_index=${idx}`;
	};
}

function setup(){
	attachForm();
	attachTableActions();
	Promise.all([loadStudents(), loadClasses()]);
}

document.addEventListener('DOMContentLoaded', setup);


