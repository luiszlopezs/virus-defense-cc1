#include "LinkedList.h"
#include <iostream>
#include <cstring>

// Constructor: Initializes the head and tail to nullptr, and the size of the list to 0.
LinkedList::LinkedList() : head(nullptr), tail(nullptr), size(0) {}

// Destructor: Iterates through the list and deletes each node to prevent memory leaks.
LinkedList::~LinkedList() {
    LinkedNode* current = head;
    while (current != nullptr) {
        LinkedNode* nextNode = current->next;
        delete current;
        current = nextNode;
    }
    head = nullptr;
    tail = nullptr;
    size = 0;
}

// append: Creates a new node, populates its fields, and adds it to the end of the list.
// Keeping track of the tail node allows this operation to be O(1).
void LinkedList::append(int row, int col, int turn, const char* cause) {
    LinkedNode* newNode = new LinkedNode();
    newNode->event.row = row;
    newNode->event.col = col;
    newNode->event.turn = turn;
    
    // Copy the cause string safely, ensuring it does not overflow and is null-terminated.
    std::strncpy(newNode->event.cause, cause, sizeof(newNode->event.cause) - 1);
    newNode->event.cause[sizeof(newNode->event.cause) - 1] = '\0';
    newNode->next = nullptr;

    if (head == nullptr) {
        head = newNode;
        tail = newNode;
    } else {
        tail->next = newNode;
        tail = newNode;
    }
    size++;
}

// getSize: Returns the current size (number of elements) in the list in O(1) time.
int LinkedList::getSize() const {
    return size;
}

// printAll: Traverses the list from head to tail and prints each infection event.
void LinkedList::printAll() const {
    LinkedNode* current = head;
    while (current != nullptr) {
        std::cout << "Turn " << current->event.turn << ": Infection at ("
                  << current->event.row << "," << current->event.col
                  << ") caused by " << current->event.cause << std::endl;
        current = current->next;
    }
}

// toArray: Copies the events into a pre-allocated array of InfectionEvents.
// This allows the list data to be formatted into JSON easily. O(N) complexity.
void LinkedList::toArray(InfectionEvent* out, int& count) const {
    LinkedNode* current = head;
    int idx = 0;
    while (current != nullptr) {
        out[idx] = current->event;
        idx++;
        current = current->next;
    }
    count = idx;
}
