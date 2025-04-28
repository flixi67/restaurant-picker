// debugbug.js
const { loadRestaurantsFromCSV } = require('./loadRestaurantsFromCSV');

console.log("🍽️ Iniciando testes para loadRestaurantsFromCSV\n");

// Teste 1: Meeting ID existente (10003)
loadRestaurantsFromCSV(10003, restaurants => {
    console.log("🔍 Teste 1: Meeting ID 10003 (existente)");
    
    if (!restaurants || restaurants.length === 0) {
        console.log("❌ Nenhum restaurante encontrado");
        return;
    }

    console.log(`✅ ${restaurants.length} restaurantes encontrados`);
    console.log("📋 Primeiro restaurante:", {
        name: restaurants[0].name,
        lat: restaurants[0].lat,
        lng: restaurants[0].lng,
        vegetarian: restaurants[0].vegetarian
    });

    // Teste adicional de tipos
    console.log("\n🧪 Verificação de tipos:");
    console.log("Nome é string?", typeof restaurants[0].name === 'string');
    console.log("Lat é número?", typeof restaurants[0].lat === 'number');
    console.log("Vegetarian é boolean?", typeof restaurants[0].vegetarian === 'boolean');
});

// Teste 2: Meeting ID inexistente (99999)
loadRestaurantsFromCSV(99999, restaurants => {
    console.log("\n🔍 Teste 2: Meeting ID 99999 (inexistente)");
    
    if (restaurants && restaurants.length > 0) {
        console.log("❌ Restaurantes encontrados para ID inválido");
    } else {
        console.log("✅ Nenhum restaurante encontrado (comportamento esperado)");
    }
});