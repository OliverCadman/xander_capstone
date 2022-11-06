document.addEventListener('DOMContentLoaded', () => {
    const app = Vue.createApp({
        data() {
            return {
                message: 'Hello World!'
            }
        }
    })

    app.mount('#app');
})