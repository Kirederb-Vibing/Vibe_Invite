(function () {
    function tilfoejMedlemFelt() {
        const container = document.getElementById('medlem-felter');
        const template = document.querySelector('.medlem-raekke');
        const newRow = template.cloneNode(true);
        newRow.querySelectorAll('input').forEach(input => {
            if (input.type === 'text' || input.type === 'email') {
                input.value = '';
            } else if (input.type === 'checkbox') {
                input.checked = true;
            }
        });
        container.appendChild(newRow);
        const navnInput = newRow.querySelector('input[name="medlem_navn[]"]');
        if (navnInput) navnInput.focus();
    }

    function fjernRaekke(event) {
        if (!event.target.classList.contains('fjern-knap')) return;
        const raekke = event.target.closest('.medlem-raekke');
        if (!raekke) return;

        const parent = raekke.parentElement;
        const alleRaekker = parent.querySelectorAll('.medlem-raekke');
        if (alleRaekker.length <= 1) {
            raekke.querySelectorAll('input[type="text"], input[type="email"]').forEach(input => {
                input.value = '';
            });
            return;
        }
        raekke.remove();
    }

    function kopierLink() {
        const knap = document.getElementById('kopier-knap');
        const linkFelt = document.getElementById('rsvp-link');
        if (!knap || !linkFelt) return;

        knap.addEventListener('click', function () {
            linkFelt.select();
            linkFelt.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(linkFelt.value).then(function () {
                const oprindelig = knap.textContent;
                knap.textContent = '✓ Kopieret';
                setTimeout(function () { knap.textContent = oprindelig; }, 1500);
            });
        });
    }

    function bindCheckboxFix() {
    const form = document.querySelector('form');
    if (!form) return;
    form.addEventListener('submit', function () {
        const checkboxes = document.querySelectorAll('input[name^="medlem_send_invitation["]');
        checkboxes.forEach(cb => {
            // Sæt value til "0" for unchecked checkboxes
            if (!cb.checked) {
                cb.value = '0';
            }
            // Tving checkbox til at blive sendt med (checked)
            cb.checked = true;
        });
    });
}

    document.addEventListener('DOMContentLoaded', function () {
        const tilfoejMedlemKnap = document.getElementById('tilfoej-medlem');
        if (tilfoejMedlemKnap) {
            tilfoejMedlemKnap.addEventListener('click', tilfoejMedlemFelt);
        }
        document.addEventListener('click', fjernRaekke);
        kopierLink();
        bindCheckboxFix();
    });
})();