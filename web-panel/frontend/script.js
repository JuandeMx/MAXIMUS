/* Maximus Web Panel - Interaction v1.0 */

const modal = document.getElementById('createModal');
const resultModal = document.getElementById('resultModal');
const createForm = document.getElementById('createForm');
const modalTitle = document.getElementById('modalTitle');
const protocolInput = document.getElementById('protocolType');
const resultData = document.getElementById('resultData');

function openModal(type) {
    protocolInput.value = type;
    modalTitle.innerHTML = `Crear Cuenta <span>${type.toUpperCase()}</span>`;
    
    // Toggle SNI field for Hysteria
    const sniGroup = document.getElementById('sniGroup');
    if (type === 'hysteria') {
        sniGroup.style.display = 'block';
    } else {
        sniGroup.style.display = 'none';
    }

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.style.display = 'none';
    resultModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    resetForm();
}

function resetForm() {
    createForm.reset();
    document.querySelector('.loader').style.display = 'none';
    document.querySelector('.btn-text').style.display = 'block';
}

async function handleCreate(e) {
    e.preventDefault();
    
    const protocol = protocolInput.value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const sni = document.getElementById('sni').value;
    
    // If protocol is UDP, we use the SSH endpoint logic on backend
    const apiEndpoint = (protocol === 'udp') ? '/api/create/ssh' : `/api/create/${protocol}`;
    
    const submitBtn = e.target.querySelector('.btn-submit');
    const loader = submitBtn.querySelector('.loader');
    const btnText = submitBtn.querySelector('.btn-text');
    
    // Show Loading
    loader.style.display = 'block';
    btnText.style.display = 'none';
    submitBtn.disabled = true;

    try {
        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, sni })
        });

        const data = await response.json();

        if (response.ok) {
            showResult(data, protocol);
        } else {
            alert(`Error: ${data.error || 'No se pudo crear la cuenta'}`);
        }
    } catch (err) {
        console.error(err);
        alert('Error de conexión con el servidor.');
    } finally {
        loader.style.display = 'none';
        btnText.style.display = 'block';
        submitBtn.disabled = false;
    }
}

function showResult(data, protocol) {
    modal.style.display = 'none';
    resultModal.style.display = 'flex';
    
    let info = "";
    
    if (protocol === 'ssh') {
        info = `--- DATOS DE CUENTA SSH ---\n`;
        info += `IP: ${data.server_ip}\n`;
        info += `Usuario: ${data.username}\n`;
        info += `Contraseña: ${data.password}\n`;
        info += `Vencimiento: ${data.expiry}\n`;
        info += `Puertos: 443, 80, 22, 7300\n`;
        info += `---------------------------`;
    } else if (protocol === 'udp') {
        info = `${data.server_ip}:1-65535@${data.username}:${data.password}`;
    } else if (protocol === 'hysteria') {
        info = `--- DATOS HYSTERIA v2 ---\n`;
        info += `Usuario: ${data.username}\n`;
        info += `Password: ${data.password}\n`;
        info += `Vencimiento: ${data.expiry}\n\n`;
        info += `LINK DE CONFIGURACIÓN:\n${data.link}`;
    }
    
    resultData.textContent = info;
}

function copyResult() {
    const text = resultData.textContent;
    navigator.clipboard.writeText(text).then(() => {
        const copyBtn = document.querySelector('.btn-copy');
        const originalHtml = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> ¡Copiado!';
        copyBtn.style.color = '#00ff00';
        copyBtn.style.borderColor = '#00ff00';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHtml;
            copyBtn.style.color = 'var(--primary)';
            copyBtn.style.borderColor = 'var(--primary)';
        }, 2000);
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == modal || event.target == resultModal) {
        closeModal();
    }
}
