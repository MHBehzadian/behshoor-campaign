(function () {
  const me = getMe();
  if (getToken() && me) {
    window.location.href = `${me.role}.html`;
    return;
  }

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("error");
    errorEl.textContent = "";
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
      const { access_token } = await api("/auth/login", {
        method: "POST",
        body: { username, password },
      });
      setToken(access_token);
      const me = await api("/auth/me");
      setMe(me);
      window.location.href = `${me.role}.html`;
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
})();
