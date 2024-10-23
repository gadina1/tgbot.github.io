# tgbot.github.io
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Игра с изображением круга</title>
    <style>
        body {
            background-color: #e0e0e0; /* Очень светлый серый фон */
            font-family: 'Arial', sans-serif;
            text-align: center;
            margin: 0;
            padding: 50px 0;
            color: #333;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        #money {
            font-size: 36px;
            margin: 20px 0;
            color: #27ae60;
            font-weight: bold;
            padding: 20px;
            border-radius: 10px;
            background-color: #dcdcdc; /* Серый фон для денег */
            border: 3px solid #8e44ad; /* Фиолетовая граница */
            display: inline-block; /* Чтобы фон работал корректно */
        }
        #progress-text {
            font-size: 20px;
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
            background-color: #dcdcdc; /* Серый фон для прогресса */
            border: 3px solid #8e44ad; /* Фиолетовая граница */
            display: inline-block; /* Чтобы фон работал корректно */
        }
        #circle {
            width: 100px; /* Диаметр изображения круга */
            height: 100px;
            background-image: url('https://www.numizmatik.ru/images/shopcoins/2000/01/640/391/1640391_r.jpg'); /* Путь к изображению круга */
            background-size: cover; /* Заполнение элемента изображением */
            border-radius: 50%; /* Делает элемент круглым */
            position: relative;
            animation: spin 0.5s linear infinite; /* Крутится быстро и плавно */
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        #earnings {
            font-size: 24px;
            margin-top: 10px;
            color: #27ae60; /* Зеленый цвет для добавленных денег */
        }
        #withdraw-button {
            margin-top: 20px;
            padding: 10px 20px;
            font-size: 18px;
            color: white;
            background-color: #8e44ad; /* Фиолетовый цвет кнопки */
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        #withdraw-button:hover {
            background-color: #9b59b6; /* Цвет кнопки при наведении */
        }
        #warning {
            display: none;
            margin-top: 20px;
            padding: 10px;
            border: 2px solid #e74c3c; /* Красная рамка для предупреждения */
            background-color: #f8d7da; /* Светлый красный фон */
            color: #721c24; /* Темно-красный текст */
            border-radius: 5px;
        }
        #ok-button {
            margin-top: 10px;
            padding: 5px 10px;
            font-size: 16px;
            color: white;
            background-color: #27ae60; /* Зеленый цвет кнопки */
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        #ok-button:hover {
            background-color: #2ecc71; /* Цвет кнопки при наведении */
        }
    </style>
</head>
<body>
    <div id="money">Деньги: 0 руб.</div>
    <div id="progress-text">Прогресс: 0%</div>
    <div id="circle"></div>
    <div id="earnings">+ 0 руб.</div>
    <button id="withdraw-button" onclick="withdrawMoney()" disabled>Забрать деньги</button>

    <div id="warning">
        Внимание:<br>
        Ожидайте завершения сессии, чтобы зафиксировать прибыль. Не закрывайте эту страницу до окончания сессии. Примерное время ожидания: 4 мин.
        <button id="ok-button" onclick="closeWarning()">Понятно</button>
    </div>

    <script>
        let money = 0;
        let interval;
        let gameDuration;
        let elapsedTime = 0;

        function startGame() {
            gameDuration = Math.floor(Math.random() * 6 + 5) * 60; // от 300 до 600 секунд
            elapsedTime = 0;
            money = 0;
            document.getElementById('money').innerText = `Деньги: ${money} руб.`;
            document.getElementById('progress-text').innerText = 'Прогресс: 0%';
            document.getElementById('earnings').innerText = '+ 0 руб.';
            document.getElementById('withdraw-button').disabled = true; // Деактивируем кнопку
            document.getElementById('warning').style.display = 'none'; // Скрываем предупреждение

            interval = setInterval(() => {
                elapsedTime++;

                // Добавляем случайное количество денег (1 или 2) каждые 3 секунды
                if (elapsedTime % 3 === 0) {
                    const earnings = Math.random() < 0.5 ? 1 : 2; // 50% вероятность 1 или 2 рубля
                    money += earnings;
                    document.getElementById('money').innerText = `Деньги: ${money} руб.`;
                    document.getElementById('earnings').innerText = `+ ${earnings} руб.`; // Показываем добавленные деньги
                }

                // Обновляем прогресс
                const progressPercent = Math.floor((elapsedTime / gameDuration) * 100);
                document.getElementById('progress-text').innerText = `Прогресс: ${progressPercent}%`;

                // Проверяем, можно ли активировать кнопку "Забрать деньги"
                if (elapsedTime >= 0) { // 4 минуты = 240 секунд
                    document.getElementById('withdraw-button').disabled = false; // Активируем кнопку
                }

                // Проверяем, закончилась ли игра
                if (elapsedTime >= gameDuration) {
                    stopGame();
                }
            }, 1000);
        }

        function stopGame() {
            clearInterval(interval);
            alert(`Вы закончили игру! У вас ${money} рублей.`);
        }

        function withdrawMoney() {
            if (elapsedTime < 240) {
                document.getElementById('warning').style.display = 'block'; // Показываем предупреждение
            } else {
                stopGame(); // Закрываем игру и показываем количество денег
                alert(`Вы забрали ${money} рублей.`);
                money = 0; // Обнуляем деньги после забирания
                document.getElementById('money').innerText = `Деньги: ${money} руб.`;
                document.getElementById('withdraw-button').disabled = true; // Деактивируем кнопку снова
            }
        }

        function closeWarning() {
            document.getElementById('warning').style.display = 'none'; // Скрываем предупреждение
        }

        // Запускаем игру автоматически
        startGame();
    </script>
</body>
</html>
