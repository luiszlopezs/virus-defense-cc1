#ifndef VIRUS_DEFENSE_LINKED_LIST_H
#define VIRUS_DEFENSE_LINKED_LIST_H

#include <cstdio>
#include <cstring>

struct InfectionEvent {
    int row;
    int col;
    int turn;
    char cause[32];
};

struct InfectionNode {
    InfectionEvent event;
    InfectionNode* next;
};

class LinkedList {
private:
    InfectionNode* head;
    InfectionNode* tail;
    int size;

public:
    LinkedList();
    ~LinkedList();

    void clear();
    void append(int row, int col, int turn, const char* cause);
    int getSize() const;
    void printAll() const;
    void toArray(InfectionEvent* out, int& count) const;
};

#endif
