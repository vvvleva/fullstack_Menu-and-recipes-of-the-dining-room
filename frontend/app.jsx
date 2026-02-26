const { BrowserRouter, Routes, Route, NavLink } = ReactRouterDOM;

function Navigation() {
  return (
    <nav className="spa-nav">
      <NavLink to="/" end className="spa-link">
        Меню
      </NavLink>
      <NavLink to="/profile" className="spa-link">
        Профиль
      </NavLink>
      <NavLink to="/about" className="spa-link">
        О проекте
      </NavLink>
    </nav>
  );
}

function Layout() {
  return (
    <div className="spa-card">
      <header className="spa-header">
        <div className="spa-title">SPA-панель столовой</div>
        <div className="spa-description">
          Демонстрация клиентской маршрутизации (React Router) для будущих CRUD, авторизации и интеграции с API.
        </div>
      </header>

      <Navigation />

      <main className="spa-main">
        <Routes>
          <Route path="/" element={<MenuPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  );
}

function MenuPage() {
  return (
    <section>
      <h3>Меню на сегодня</h3>
      <p className="spa-text">
        Здесь в следующих лабораторных (ЛР №4 и №7) будут отображаться реальные данные из эндпоинтов
        <code> /api/menu </code> и <code>/api/menu/&lt;id&gt;</code> c обработкой загрузки и ошибок.
      </p>
      <ul className="spa-list">
        <li>Список блюд с ценой, весом и категорией</li>
        <li>Метка «Безопасно»/«Опасно» по результатам анализа аллергенов</li>
        <li>Кнопка перехода к подробной карточке блюда</li>
      </ul>
    </section>
  );
}

function ProfilePage() {
  return (
    <section>
      <h3>Профиль и аллергены</h3>
      <p className="spa-text">
        Экран для хранения предпочтений пользователя: аллергены, диета, история выборов.
        В дальнейших ЛР (№5–6) здесь появятся авторизация и защита маршрутов.
      </p>
      <ul className="spa-list">
        <li>Выбор аллергенов (орехи, лактоза, глютен, морепродукты)</li>
        <li>Выбор диеты (веган, безглютеновая и др.)</li>
        <li>Сохранение настроек после входа в систему</li>
      </ul>
    </section>
  );
}

function AboutPage() {
  return (
    <section>
      <h3>Структура проекта и чек‑поинты</h3>
      <p className="spa-text">
        Текущая версия покрывает ЛР №1–3. Далее планируется добавить CRUD для блюд, авторизацию и JWT‑защиту API.
      </p>
      <ol className="spa-list spa-list-ordered">
        <li>ЛР №4 — CRUD для меню: создание, изменение и удаление блюд.</li>
        <li>ЛР №5 — клиентская авторизация, работа с токенами.</li>
        <li>ЛР №6 — защита API: JWT, middleware, роли.</li>
        <li>ЛР №7 — полноценная интеграция: загрузка меню, анализ аллергенов на фронтенде.</li>
      </ol>
    </section>
  );
}

function App() {
  return (
    <ReactRouterDOM.BrowserRouter>
      <Layout />
    </ReactRouterDOM.BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById("spa-root"));
root.render(<App />);

