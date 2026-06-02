#include "LinkedList.h"

LinkedList::LinkedList() : head(nullptr), tail(nullptr), size(0) {}

LinkedList::~LinkedList() {
    clear();
}

void LinkedList::clear() {
    InfectionNode* current = head;
    while (current != nullptr) {
        InfectionNode* next = current->next;
        delete current;
        current = next;
    }
    head = nullptr;
    tail = nullptr;
    size = 0;
}

void LinkedList::append(int row, int col, int turn, const char* cause) {
    InfectionNode* node = new InfectionNode;
    node->event.row = row;
    node->event.col = col;
    node->event.turn = turn;
    std::snprintf(node->event.cause, sizeof(node->event.cause), "%s", cause != nullptr ? cause : "unknown");
    node->next = nullptr;

    if (tail == nullptr) {
        head = node;
        tail = node;
    } else {
        tail->next = node;
        tail = node;
    }
    size++;
}

int LinkedList::getSize() const {
    return size;
}

void LinkedList::printAll() const {
    const InfectionNode* current = head;
    while (current != nullptr) {
        std::printf("turn=%d row=%d col=%d cause=%s\n",
                    current->event.turn,
                    current->event.row,
                    current->event.col,
                    current->event.cause);
        current = current->next;
    }
}

void LinkedList::toArray(InfectionEvent* out, int& count) const {
    count = 0;
    const InfectionNode* current = head;
    while (current != nullptr) {
        out[count] = current->event;
        count++;
        current = current->next;
    }
}
