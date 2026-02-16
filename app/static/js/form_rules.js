document.addEventListener("DOMContentLoaded", function () {

    const rules = {

        numero_cliente: {
            maxLength: 10,
            format: value => value.replace(/\D/g, '')
        },

        numero_contrato: {
            maxLength: 12,
            format: value => value.replace(/\D/g, '')
        },

        codigo_postal: {
            maxLength: 5,
            format: value => value.replace(/\D/g, '')
        },

        telefono: {
            maxLength: 12,
            format: value => {
                let digits = value.replace(/\D/g, '').substring(0, 10);

                if (digits.length >= 7)
                    return digits.replace(/(\d{3})(\d{3})(\d+)/, '$1-$2-$3');
                if (digits.length >= 4)
                    return digits.replace(/(\d{3})(\d+)/, '$1-$2');

                return digits;
            }
        },

        rfc: {
            maxLength: 15,
            format: value => {
                value = value.toUpperCase().replace(/[^A-Z0-9]/g, '');

                if (value.length > 13) value = value.substring(0, 13);

                if (value.length > 9)
                    return value.replace(/(.{4})(.{6})(.*)/, '$1-$2-$3');
                if (value.length > 4)
                    return value.replace(/(.{4})(.*)/, '$1-$2');

                return value;
            }
        },

        email: {
            format: value => value.toLowerCase()
        }

    };

    document.querySelectorAll("[data-type]").forEach(input => {

        const type = input.dataset.type;
        if (!rules[type]) return;

        input.addEventListener("input", function () {

            let rule = rules[type];
            let value = this.value;

            if (rule.format) {
                value = rule.format(value);
            }

            if (rule.maxLength) {
                this.maxLength = rule.maxLength;
            }

            this.value = value;
        });

    });

});
