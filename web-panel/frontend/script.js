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
    const days = document.getElementById('days').value;
    
    const submitBtn = e.target.querySelector('.btn-submit');
    const loader = submitBtn.querySelector('.loader');
    const btnText = submitBtn.querySelector('.btn-text');
    
    // Show Loading
    loader.style.display = 'block';
    btnText.style.display = 'none';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`/api/create/${protocol}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, days })
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
    
    let info = `USUARIO: ${data.username}\n`;
    info += `PASSWORD: ${data.password}\n`;
    info += `EXPIRACIÓN: ${data.expiry}\n`;
    
    if (data.link) {
        info += `\nENLACE CONFIG:\n${data.link}`;
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
