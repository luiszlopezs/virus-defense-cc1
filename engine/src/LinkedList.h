#ifndef LINKEDLIST_H
#define LINKEDLIST_H

// InfectionEvent stores the coordinates, the turn, and the cause of a specific infection event.
struct InfectionEvent {
    int row;
    int col;
    int turn;
    char cause[32];
};

// LinkedNode represents a single node in our singly linked list.
struct LinkedNode {
    InfectionEvent event;
    LinkedNode* next;
};

// LinkedList manages a singly linked list of infection events, supporting O(1) appends.
class LinkedList {
private:
    LinkedNode* head;
    LinkedNode* tail;
    int size;

public:
    LinkedList();
    ~LinkedList();

    void append(int row, int col, int turn, const char* cause);
    int getSize() const;
    void printAll() const;
    void toArray(InfectionEvent* out, int& count) const;
};

#endif // LINKEDLIST_H
