<template>
  <router-view />
</template>

<style>
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background-color: #f4f6f8;
}

.page-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.card {
  background: white;
  padding: 40px;
  width: 420px;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
  margin-bottom: 25px;
}

input,
select,
button {
  width: 100%;
  padding: 10px;
  margin: 10px 0;
  font-size: 14px;
}

button {
  background-color: #3498db;
  color: white;
  border: none;
  cursor: pointer;
  transition: 0.2s;
}

button:hover {
  background-color: #2980b9;
}

button.danger {
  background-color: #d9534f;
}

button.danger:hover {
  background-color: #c9302c;
}

hr {
  margin: 20px 0;
}
</style>