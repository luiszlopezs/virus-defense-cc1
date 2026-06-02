#include "GameEngine.h"

#include <chrono>
#include <cstring>
#include <iostream>
#include <thread>

int main() {
    GameEngine engine;
    engine.writeInputNone();
    engine.writeStateJSON();

    std::cout << "Virus Defense C++ engine is running. Press Ctrl+C to stop.\n";

    while (engine.isRunning()) {
        EngineInput input = engine.readInputJSON();
        bool processed = engine.applyInput(input);
        if (processed || std::strcmp(input.action, "none") != 0) {
            engine.writeStateJSON();
            engine.writeInputNone();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(120));
    }

    engine.writeStateJSON();
    engine.writeInputNone();
    std::cout << "Virus Defense C++ engine stopped.\n";
    return 0;
}
